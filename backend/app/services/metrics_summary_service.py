import time
import logging
from typing import Any, Dict, Optional

from ..models import Instance
from .system_metrics_service import system_metrics_service
from .slowlog_service import slowlog_service
from .direct_mysql_metrics_service import direct_mysql_metrics_service

'''
   配置优化页面：获取实例的指标汇总
   架构优化页面：提供性能数据
'''

logger = logging.getLogger(__name__)


'''汇总系统与数据库的关键只读指标（最小可行版）。
    - 系统：CPU、内存、磁盘（基于 psutil）
    - MySQL：连接/并发、锁等待（来自 SHOW GLOBAL STATUS/VARIABLES）
    - 慢日志：总条数（优先 TABLE 输出，通过 mysql.slow_log 统计）
'''
class MetricsSummaryService:
 

    def get_summary(self, inst: Instance):
        summary: Dict[str, Any] = {
            'system': {
                'cpu_usage': None,
                'memory_usage': None,
                'disk_usage': None,
                'network_io_mbps': None,
            },
            'mysql': {
                'threads_connected': None,
                'threads_running': None,
                'innodb_row_lock_waits': None,
                'innodb_row_lock_time_ms': None,
                'connection_pressure_pct': None,
                'cache_hit_rate': None,  # 0~100
                'deadlocks': None,       # 累计值（若启用 innodb_metrics）
                'slow_query_ratio': None,  # 慢查询比例
                'avg_response_time_ms': None,  # 平均响应时间
                'index_usage_rate': None,  # 索引使用率
                'max_connections': None,   # 最大连接数
                'replication_delay_ms': None,  # 主从延迟（毫秒）
                'peak_connections': None,  # 峰值连接数（Max_used_connections）
                'transactions_total': None,  # 事务总数（近实时累计值）
            },
            'slowlog': {
                'total_recent': None,
                'note': '',
            },
            # 新增：性能指标（若 exporter 已接入则给出数值，否则保持为 None）
            'perf': {
                'qps': None,
                'tps': None,
                'p95_latency_ms': None,
                'io_latency_ms': None,
                'redo_write_latency_ms': None,  # 平均写延迟（ms）
                'slowest_query_ms': None,
            },
            'generated_at': int(time.time())
        }

        # 系统指标采集（仅使用 psutil）
        try:
            if system_metrics_service.health_check():
                sys_metrics = system_metrics_service.get_all_metrics()
                summary['system']['cpu_usage'] = sys_metrics.get('cpu_usage')
                summary['system']['memory_usage'] = sys_metrics.get('memory_usage')
                summary['system']['disk_usage'] = sys_metrics.get('disk_usage')
                # 使用 psutil 估算的磁盘 I/O 延迟
                summary['perf']['io_latency_ms'] = sys_metrics.get('io_latency_ms')
                logger.info("使用 psutil 采集系统指标")
            else:
                logger.warning("系统指标采集失败：psutil 不可用")

            # 计算网络IO速率（MB/s），基于 psutil 简单采样
            try:
                import psutil
                c1 = psutil.net_io_counters()
                t1 = time.time()
                time.sleep(1)
                c2 = psutil.net_io_counters()
                t2 = time.time()
                dt = max(1e-3, t2 - t1)
                bytes_delta = max(0, (c2.bytes_sent - c1.bytes_sent)) + max(0, (c2.bytes_recv - c1.bytes_recv))
                summary['system']['network_io_mbps'] = round(bytes_delta / dt / 1048576, 2)
            except Exception as e:
                logger.info(f"网络IO采集失败: {e}")
        except Exception as e:
            logger.info(f"系统指标采集失败: {e}")

        # MySQL 状态（优先使用直接查询服务）
        # 使用direct_mysql_metrics_service获取MySQL指标 来自direct_mysql_metrics_service.py
        direct_metrics = direct_mysql_metrics_service.get_all_direct_metrics(inst)
        
        # 直接使用获取的指标数据
        summary['mysql']['threads_connected'] = direct_metrics.get('threads_connected')
        summary['mysql']['threads_running'] = direct_metrics.get('threads_running')
        summary['mysql']['innodb_row_lock_waits'] = direct_metrics.get('innodb_row_lock_waits')
        summary['mysql']['innodb_row_lock_time_ms'] = direct_metrics.get('innodb_row_lock_time_ms')
        summary['mysql']['cache_hit_rate'] = direct_metrics.get('cache_hit_rate')
        summary['mysql']['deadlocks'] = direct_metrics.get('deadlocks')
        summary['mysql']['slow_query_ratio'] = direct_metrics.get('slow_query_ratio')
        summary['mysql']['avg_response_time_ms'] = direct_metrics.get('avg_response_time_ms')
        summary['mysql']['index_usage_rate'] = direct_metrics.get('index_usage_rate')
        summary['mysql']['max_connections'] = direct_metrics.get('max_connections')
        summary['mysql']['replication_delay_ms'] = direct_metrics.get('replication_delay_ms')
        summary['mysql']['peak_connections'] = direct_metrics.get('peak_connections')
        summary['mysql']['transactions_total'] = direct_metrics.get('transactions_total')
        summary['perf']['redo_write_latency_ms'] = direct_metrics.get('redo_write_latency_ms')
        summary['perf']['slowest_query_ms'] = direct_metrics.get('slowest_query_ms')
        
        # 更新QPS、TPS、P95延迟等关键指标
        if direct_metrics.get('qps') is not None:
            summary['perf']['qps'] = direct_metrics.get('qps')
        if direct_metrics.get('tps') is not None:
            summary['perf']['tps'] = direct_metrics.get('tps')
        if direct_metrics.get('p95_latency_ms') is not None:
            summary['perf']['p95_latency_ms'] = direct_metrics.get('p95_latency_ms')

        # 3) 慢日志总数（TABLE 输出）
        ok, data, msg = slowlog_service.list_from_table(inst, page=1, page_size=1, filters={})
        if ok:
            summary['slowlog']['total_recent'] = int(data.get('total') or 0)
        else:
            summary['slowlog']['note'] = msg or '慢日志查询失败'

        return summary

    # 新增：支持在一次接口内进行窗口二次采样（简化版，委托服务层）
    def get_summary_with_window(self, inst: Instance, window_s: int = 6):
        summary = self.get_summary(inst)
        try:
            sleep_seconds = max(1, int(window_s))
        except Exception:
            sleep_seconds = 6
        
        # 强制执行窗口采样，失败时抛出异常
        qps_tps = direct_mysql_metrics_service.get_qps_tps_window(inst, sleep_seconds)
        if isinstance(qps_tps, dict):
            # 检查是否有错误信息
            if qps_tps.get('error'):
                raise Exception(f"窗口采样失败：{qps_tps.get('error')}")
            
            # 检查是否获取到有效的QPS/TPS数据
            if qps_tps.get('qps') is None and qps_tps.get('tps') is None:
                raise Exception("窗口采样失败：未获取到有效的QPS/TPS数据")
            
            if qps_tps.get('qps') is not None:
                summary['perf']['qps'] = qps_tps.get('qps')
            if qps_tps.get('tps') is not None:
                summary['perf']['tps'] = qps_tps.get('tps')
            if qps_tps.get('transactions_total') is not None:
                summary['mysql']['transactions_total'] = qps_tps.get('transactions_total')
        else:
            raise Exception("窗口采样失败：无法获取QPS/TPS数据")
        
        return summary


metrics_summary_service = MetricsSummaryService()