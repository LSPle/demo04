import time
import logging
from typing import Any, Dict, Optional

from ..models import Instance
from .prometheus_service import prometheus_service
from .slowlog_service import slowlog_service
from .config_optimization_service import config_collector

logger = logging.getLogger(__name__)


class MetricsSummaryService:
    """汇总系统与数据库的关键只读指标（最小可行版）。
    - 系统：CPU、内存、磁盘（来自 Prometheus，如不可用则为 None）
    - MySQL：连接/并发、锁等待（来自 SHOW GLOBAL STATUS/VARIABLES）
    - 慢日志：总条数（优先 TABLE 输出，通过 mysql.slow_log 统计）
    """

    def get_summary(self, inst: Instance) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            'system': {
                'cpu_usage': None,
                'memory_usage': None,
                'disk_usage': None,  # { used_gb, total_gb, usage_percent, display }
            },
            'mysql': {
                'threads_connected': None,
                'threads_running': None,
                'innodb_row_lock_waits': None,
                'innodb_row_lock_time_ms': None,
                'connection_pressure_pct': None,
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

        # 1) Prometheus 指标
        try:
            prom = prometheus_service.get_all_metrics('mysqld') if prometheus_service else {}
            if isinstance(prom, dict) and prom:
                summary['system']['cpu_usage'] = prom.get('cpu_usage')
                summary['system']['memory_usage'] = prom.get('memory_usage')
                summary['system']['disk_usage'] = prom.get('disk_usage')

            # 新增：尝试获取 QPS/TPS/P95/磁盘 I/O 延迟
            try:
                qps = prometheus_service.get_qps()
            except Exception:
                qps = None
            try:
                tps = prometheus_service.get_tps()
            except Exception:
                tps = None
            try:
                p95 = prometheus_service.get_p95_latency_ms()
            except Exception:
                p95 = None
            try:
                io_lat = prometheus_service.get_disk_io_latency_ms()
            except Exception:
                io_lat = None

            # 写入 perf 数值（可能为 None）
            summary['perf']['qps'] = qps
            summary['perf']['tps'] = tps
            summary['perf']['p95_latency_ms'] = p95
            summary['perf']['io_latency_ms'] = io_lat

            # 若取到了有效数值，顺带把 unsupported 中对应项替换为数值，兼容旧消费端
            def _is_num(x):
                return isinstance(x, (int, float)) and not (x != x)
            if _is_num(qps):
                summary['unsupported']['qps'] = round(qps, 2)
            if _is_num(tps):
                summary['unsupported']['tps'] = round(tps, 2)
            if _is_num(p95):
                summary['unsupported']['p95_latency_ms'] = round(p95, 2)
            if _is_num(io_lat):
                summary['unsupported']['io_latency_ms'] = round(io_lat, 2)
        except Exception as e:
            logger.info(f"Prometheus 指标获取失败: {e}")

        # 2) MySQL 状态（复用配置采集器，避免重复实现）
        try:
            ok, data, _ = config_collector.collect(inst)
            if ok:
                raw = data.get('raw') or {}
                summary['mysql']['threads_connected'] = raw.get('threads_connected')
                summary['mysql']['threads_running'] = raw.get('threads_running')
                summary['mysql']['innodb_row_lock_waits'] = raw.get('innodb_row_lock_waits')
                summary['mysql']['innodb_row_lock_time_ms'] = raw.get('innodb_row_lock_time')
                summary['mysql']['connection_pressure_pct'] = raw.get('connection_pressure_pct')
        except Exception as e:
            logger.info(f"MySQL 状态采集失败: {e}")

        # 3) 慢日志总数（优先 TABLE 输出）
        try:
            ok, data, msg = slowlog_service.list_from_table(inst, page=1, page_size=1, filters={})
            if ok:
                summary['slowlog']['total_recent'] = int(data.get('total') or 0)
            else:
                # 记录原因但不中断
                ov = (data or {}).get('overview') or {}
                note = msg or ''
                if ov:
                    note = f"{note}（log_output={ov.get('log_output','')}）"
                summary['slowlog']['note'] = note
        except Exception as e:
            logger.info(f"慢日志统计失败: {e}")

        return summary


metrics_summary_service = MetricsSummaryService()