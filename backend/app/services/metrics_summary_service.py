import time
import logging
from typing import Any, Dict, Optional

from ..models import Instance
from .prometheus_service import prometheus_service
from .system_metrics_service import system_metrics_service
from .slowlog_service import slowlog_service
from .direct_mysql_metrics_service import direct_mysql_metrics_service

'''
   配置优化页面：获取实例的指标汇总
   架构优化页面：提供性能数据
'''

logger = logging.getLogger(__name__)


'''汇总系统与数据库的关键只读指标（最小可行版）。
    - 系统：CPU、内存、磁盘（来自 Prometheus，如不可用则为 None）
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
            },
            # 兼容保留：之前作为占位标记的 unsupported 字段
            'unsupported': {
                'qps': 'unsupported',
                'tps': 'unsupported',
                'p95_latency_ms': 'unsupported',
                'io_latency_ms': 'unsupported'
            },
            'generated_at': int(time.time())
        }

        # 系统指标采集（优先使用psutil，备选Prometheus）
        try:
            # 首先尝试使用轻量级psutil采集
            if system_metrics_service.health_check():
                sys_metrics = system_metrics_service.get_all_metrics()
                summary['system']['cpu_usage'] = sys_metrics.get('cpu_usage')
                summary['system']['memory_usage'] = sys_metrics.get('memory_usage')
                summary['system']['disk_usage'] = sys_metrics.get('disk_usage')
                logger.info("使用psutil采集系统指标")
            else:
                # 备选：使用Prometheus采集
                # prom = prometheus_service.get_all_metrics('mysqld') if prometheus_service else {}
                if prometheus_service:
                    prom = prometheus_service.get_all_metrics('mysqld')
                else:
                    prom = {}
                if isinstance(prom, dict) and prom:
                    summary['system']['cpu_usage'] = prom.get('cpu_usage')
                    summary['system']['memory_usage'] = prom.get('memory_usage')
                    summary['system']['disk_usage'] = prom.get('disk_usage')
                    logger.info("使用Prometheus采集系统指标")
                else:
                    logger.warning("系统指标采集失败：psutil和Prometheus均不可用")

            # 新增：尝试获取 QPS/TPS/P95/磁盘 I/O 延迟（仅在直接查询未获取到时使用Prometheus）
            if summary['perf']['qps'] is None:
                qps = prometheus_service.get_qps()
                summary['perf']['qps'] = qps
            
            if summary['perf']['tps'] is None:
                tps = prometheus_service.get_tps()
                summary['perf']['tps'] = tps
            
            if summary['perf']['p95_latency_ms'] is None:
                p95 = prometheus_service.get_p95_latency_ms()
                summary['perf']['p95_latency_ms'] = p95
            
            io_lat = prometheus_service.get_disk_io_latency_ms()
            summary['perf']['io_latency_ms'] = io_lat
        except Exception as e:
            logger.info(f"Prometheus 指标获取失败: {e}")

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
        summary['perf']['redo_write_latency_ms'] = direct_metrics.get('redo_write_latency_ms')
        
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


metrics_summary_service = MetricsSummaryService()