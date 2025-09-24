import requests
import logging
from typing import Dict, Optional, Any
from flask import current_app

'''
   prometheus服务(需要更换为mysql直接获取指标，采用psutil)
   配置优化/架构优化页面：CPU使用率、内存使用率、QPS、TPS、P95、磁盘 I/O 延迟 
'''

logger = logging.getLogger(__name__)


class PrometheusService:
    #初始化
    def __init__(self):
        self.base_url = None
        self.timeout = 10
    #获取和规范化Prometheus服务器的基础UR
    def _get_base_url(self):
        if not self.base_url:
            self.base_url = current_app.config.get('PROMETHEUS_BASE_URL', 'http://localhost:9090')
            if self.base_url.endswith('/classic/graph'):
                self.base_url = self.base_url.replace('/classic/graph', '')
        return self.base_url
    #执行rometheus查询
    def _query_prometheus(self, query: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self._get_base_url()}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', {})
            else:
                logger.error(f"Prometheus query failed: {data.get('error', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Prometheus: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying Prometheus: {e}")
            return None

    #通用模式的辅助方法
    def _query_value(self, query: str) -> Optional[float]:
        """执行查询并从第一个序列中解析单个标量值"""
        result = self._query_prometheus(query)
        if result and result.get('result'):
            try:
                return float(result['result'][0]['value'][1])
            except (IndexError, ValueError, KeyError):
                return None
        return None

    def _first_nonempty(self, queries: list[str]) -> Optional[float]:
        """按顺序尝试查询列表，返回第一个非空的数值结果"""
        for q in queries:
            val = self._query_value(q)
            if val is not None:
                return val
        return None

    def get_cpu_usage(self, service_name: str) -> Optional[float]:
        """获取服务的CPU使用率百分比"""
        # CPU使用率的PromQL查询 - 根据你的Prometheus设置调整
        query = f'100 - (avg(irate(node_cpu_seconds_total{{mode="idle",instance=~".*{service_name}.*"}}[5m])) * 100)'
        
        result = self._query_prometheus(query)
        if result and result.get('result'):
            try:
                value = float(result['result'][0]['value'][1])
                return round(value, 2)
            except (IndexError, ValueError, KeyError):
                logger.warning(f"无法解析服务 {service_name} 的CPU使用率")
        
        return None
    
    def get_memory_usage(self, service_name: str) -> Optional[float]:
        """获取服务的内存使用率百分比"""
        # 内存使用率的PromQL查询 - 根据你的Prometheus设置调整
        query = f'(1 - (node_memory_MemAvailable_bytes{{instance=~".*{service_name}.*"}} / node_memory_MemTotal_bytes{{instance=~".*{service_name}.*"}})) * 100'
        
        result = self._query_prometheus(query)
        if result and result.get('result'):
            try:
                value = float(result['result'][0]['value'][1])
                return round(value, 2)
            except (IndexError, ValueError, KeyError):
                logger.warning(f"无法解析服务 {service_name} 的内存使用率")
        
        return None
    
    def get_disk_usage(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务的磁盘使用信息"""
        # 磁盘使用率的PromQL查询
        used_query = f'node_filesystem_size_bytes{{instance=~".*{service_name}.*",fstype!="tmpfs"}} - node_filesystem_free_bytes{{instance=~".*{service_name}.*",fstype!="tmpfs"}}'
        total_query = f'node_filesystem_size_bytes{{instance=~".*{service_name}.*",fstype!="tmpfs"}}'
        
        used_result = self._query_prometheus(used_query)
        total_result = self._query_prometheus(total_query)
        
        if used_result and total_result and used_result.get('result') and total_result.get('result'):
            try:
                used_bytes = float(used_result['result'][0]['value'][1])
                total_bytes = float(total_result['result'][0]['value'][1])
                
                used_gb = round(used_bytes / (1024**3), 1)
                total_gb = round(total_bytes / (1024**3), 1)
                usage_percent = round((used_bytes / total_bytes) * 100, 2)
                
                return {
                    'used_gb': used_gb,
                    'total_gb': total_gb,
                    'usage_percent': usage_percent,
                    'storage_display': f'{used_gb}GB / {total_gb}GB'
                }
            except (IndexError, ValueError, KeyError):
                logger.warning(f"无法解析服务 {service_name} 的磁盘使用率")
        
        return None

    # 新增：MySQL QPS/TPS/P95 和磁盘IO延迟辅助方法
    def get_qps(self) -> Optional[float]:
        """基于mysql导出器指标的每秒查询数(QPS)"""
        queries = [
            # 在大多数设置中优先使用Queries而不是Questions
            'sum(rate(mysql_global_status_queries[1m]))',
            'sum(rate(mysql_global_status_questions[1m]))',
            'sum(irate(mysql_global_status_queries[5m]))',
            'sum(irate(mysql_global_status_questions[5m]))',
        ]
        val = self._first_nonempty(queries)
        return round(val, 2) if isinstance(val, (float, int)) else None

    def get_tps(self) -> Optional[float]:
        """使用提交+回滚速率的每秒事务数(TPS)"""
        queries = [
            'sum(rate(mysql_global_status_com_commit[1m])) + sum(rate(mysql_global_status_com_rollback[1m]))',
            'sum(irate(mysql_global_status_com_commit[5m])) + sum(irate(mysql_global_status_com_rollback[5m]))',
        ]
        val = self._first_nonempty(queries)
        return round(val, 2) if isinstance(val, (float, int)) else None

    def get_p95_latency_ms(self) -> Optional[float]:
        """如果直方图指标可用，近似P95查询延迟（毫秒）"""
        candidates = [
            # 通过information_schema的query_response_time插件
            '1000 * histogram_quantile(0.95, sum(rate(mysql_info_schema_query_response_time_seconds_bucket[5m])) by (le))',
            # performance_schema事件语句直方图（导出器命名可能不同）
            '1000 * histogram_quantile(0.95, sum(rate(mysql_perf_schema_events_statements_seconds_bucket[5m])) by (le))',
        ]
        for q in candidates:
            val = self._query_value(q)
            if isinstance(val, (float, int)):
                # 有时当桶为空时histogram_quantile返回NaN
                try:
                    if not (val != val):  # 过滤NaN
                        return round(val, 2)
                except Exception:
                    return round(val, 2)
        return None

    def get_disk_io_latency_ms(self, device_regex: str = ".*") -> Optional[float]:
        """平均磁盘I/O延迟（毫秒/操作），跨设备加权。
        需要node_exporter指标。使用读/写时间除以操作数作为近似值。
        """
        # 优先使用标准指标名称；为兼容性尝试备用方案
        read_time = f'sum(rate(node_disk_read_time_seconds_total[5m]))'
        write_time = f'sum(rate(node_disk_write_time_seconds_total[5m]))'
        read_ops = f'sum(rate(node_disk_reads_completed_total[5m]))'
        write_ops = f'sum(rate(node_disk_writes_completed_total[5m]))'
        
        # 如果提供了设备过滤器则应用
        if device_regex and device_regex != ".*":
            read_time = f'sum(rate(node_disk_read_time_seconds_total{{device=~"{device_regex}"}}[5m]))'
            write_time = f'sum(rate(node_disk_write_time_seconds_total{{device=~"{device_regex}"}}[5m]))'
            read_ops = f'sum(rate(node_disk_reads_completed_total{{device=~"{device_regex}"}}[5m]))'
            write_ops = f'sum(rate(node_disk_writes_completed_total{{device=~"{device_regex}"}}[5m]))'

        # 计算组合延迟 = 1000 * (sum(read_time)+sum(write_time)) / (sum(read_ops)+sum(write_ops))
        combined_query = f'1000 * (({read_time}) + ({write_time})) / (({read_ops}) + ({write_ops}))'
        val = self._query_value(combined_query)
        if isinstance(val, (float, int)):
            try:
                if not (val != val):  # NaN保护
                    return round(val, 2)
            except Exception:
                return round(val, 2)

        # 备用方案：如果读/写指标缺失，尝试io_time/ops
        io_time = 'sum(rate(node_disk_io_time_seconds_total[5m]))'
        ops_any = f'(({read_ops}) + ({write_ops}))'
        fallback = f'1000 * ({io_time}) / ({ops_any})'
        val2 = self._query_value(fallback)
        if isinstance(val2, (float, int)):
            try:
                if not (val2 != val2):
                    return round(val2, 2)
            except Exception:
                return round(val2, 2)
        return None
    
    def get_all_metrics(self, service_name: str) -> Dict[str, Any]:
        """获取服务的所有指标（CPU、内存、磁盘）"""
        metrics = {
            'service': service_name,
            'cpu_usage': self.get_cpu_usage(service_name),
            'memory_usage': self.get_memory_usage(service_name),
            'disk_usage': self.get_disk_usage(service_name),
            'timestamp': None
        }
        
        # 如果至少有一个指标，则添加时间戳
        if any(v is not None for k, v in metrics.items() if k not in ['service', 'timestamp']):
            import time
            metrics['timestamp'] = int(time.time())
        
        return metrics
    
    def health_check(self) -> bool:
        """检查Prometheus是否可访问"""
        try:
            url = f"{self._get_base_url()}/api/v1/status/config"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


# 全局实例
prometheus_service = PrometheusService()