import time
import logging
from typing import Any, Dict, Optional

from ..models import Instance
from .prometheus_service import prometheus_service
from .system_metrics_service import system_metrics_service
from .slowlog_service import slowlog_service
from .direct_mysql_metrics_service import direct_mysql_metrics_service


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

        # 1) 系统指标采集（优先使用psutil，备选Prometheus）
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
                prom = prometheus_service.get_all_metrics('mysqld') if prometheus_service else {}
                if isinstance(prom, dict) and prom:
                    summary['system']['cpu_usage'] = prom.get('cpu_usage')
                    summary['system']['memory_usage'] = prom.get('memory_usage')
                    summary['system']['disk_usage'] = prom.get('disk_usage')
                    logger.info("使用Prometheus采集系统指标")
                else:
                    logger.warning("系统指标采集失败：psutil和Prometheus均不可用")

            # 新增：尝试获取 QPS/TPS/P95/磁盘 I/O 延迟（仅在直接查询未获取到时使用Prometheus）
            if summary['perf']['qps'] is None:
                try:
                    qps = prometheus_service.get_qps()
                    summary['perf']['qps'] = qps
                    if isinstance(qps, (int, float)) and not (qps != qps):
                        summary['unsupported']['qps'] = round(qps, 2)
                except Exception:
                    pass
            
            if summary['perf']['tps'] is None:
                try:
                    tps = prometheus_service.get_tps()
                    summary['perf']['tps'] = tps
                    if isinstance(tps, (int, float)) and not (tps != tps):
                        summary['unsupported']['tps'] = round(tps, 2)
                except Exception:
                    pass
            
            if summary['perf']['p95_latency_ms'] is None:
                try:
                    p95 = prometheus_service.get_p95_latency_ms()
                    summary['perf']['p95_latency_ms'] = p95
                    if isinstance(p95, (int, float)) and not (p95 != p95):
                        summary['unsupported']['p95_latency_ms'] = round(p95, 2)
                except Exception:
                    pass
            
            try:
                io_lat = prometheus_service.get_disk_io_latency_ms()
                summary['perf']['io_latency_ms'] = io_lat
                if isinstance(io_lat, (int, float)) and not (io_lat != io_lat):
                    summary['unsupported']['io_latency_ms'] = round(io_lat, 2)
            except Exception:
                pass
        except Exception as e:
            logger.info(f"Prometheus 指标获取失败: {e}")

        # 2) MySQL 状态（优先使用直接查询服务）
        try:
            # 优先使用直接MySQL查询获取指标
            direct_metrics = direct_mysql_metrics_service.get_all_direct_metrics(inst)
            
            # 如果直接查询成功，使用直接查询结果
            if not direct_metrics.get('error'):
                logger.info(f"成功通过直接查询获取MySQL指标")
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
                
                # 更新QPS、TPS、P95延迟等关键指标映射
                if direct_metrics.get('qps') is not None:
                    summary['perf']['qps'] = direct_metrics.get('qps')
                    summary['unsupported']['qps'] = round(direct_metrics.get('qps'), 2)
                if direct_metrics.get('tps') is not None:
                    summary['perf']['tps'] = direct_metrics.get('tps')
                    summary['unsupported']['tps'] = round(direct_metrics.get('tps'), 2)
                if direct_metrics.get('p95_latency_ms') is not None:
                    summary['perf']['p95_latency_ms'] = direct_metrics.get('p95_latency_ms')
                    summary['unsupported']['p95_latency_ms'] = round(direct_metrics.get('p95_latency_ms'), 2)
            else:
                # 如果直接查询失败，回退到原有的pymysql实现
                logger.warning(f"直接查询MySQL失败: {direct_metrics.get('error')}，使用pymysql回退")
                import pymysql
                conn = pymysql.connect(
                    host=inst.host,
                    port=inst.port,
                    user=inst.username,
                    password=inst.password,
                    charset='utf8mb4',
                    connect_timeout=10
                )
                with conn.cursor() as cursor:
                    # 2.1 基础状态
                    cursor.execute("""
                        SHOW GLOBAL STATUS WHERE Variable_name IN (
                            'Threads_connected', 'Threads_running',
                            'Innodb_row_lock_waits', 'Innodb_row_lock_time',
                            'Innodb_buffer_pool_read_requests', 'Innodb_buffer_pool_reads'
                        )
                    """)
                    status_data = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    summary['mysql']['threads_connected'] = status_data.get('Threads_connected')
                    summary['mysql']['threads_running'] = status_data.get('Threads_running')
                    summary['mysql']['innodb_row_lock_waits'] = status_data.get('Innodb_row_lock_waits')
                    summary['mysql']['innodb_row_lock_time_ms'] = status_data.get('Innodb_row_lock_time')

                    # 2.2 InnoDB Buffer Pool 命中率（0~100）
                    try:
                        req = float(status_data.get('Innodb_buffer_pool_read_requests') or 0)
                        rd = float(status_data.get('Innodb_buffer_pool_reads') or 0)
                        hit = None
                        if req > 0:
                            ratio = 1.0 - (rd / req)
                            # 限制范围并转百分比
                            ratio = max(0.0, min(1.0, ratio))
                            hit = round(ratio * 100.0, 2)
                        summary['mysql']['cache_hit_rate'] = hit
                    except Exception:
                        summary['mysql']['cache_hit_rate'] = None

                    # 2.3 死锁计数（需要启用 information_schema.innodb_metrics）
                    try:
                        cursor.execute(
                            """
                            SELECT COALESCE(MAX(`count`),0)
                            FROM information_schema.innodb_metrics
                            WHERE name='lock_deadlocks' AND status='enabled'
                            """
                        )
                        row = cursor.fetchone()
                        if row is not None:
                            summary['mysql']['deadlocks'] = int(row[0] or 0)
                    except Exception:
                        # 未启用或不支持则置空
                        summary['mysql']['deadlocks'] = None

                    # 2.4 Redo 写入平均延迟（ms），来自 innodb_metrics（log_write_time 为微秒累计）
                    try:
                        cursor.execute(
                            """
                            SELECT name, `count` FROM information_schema.innodb_metrics
                            WHERE status='enabled' AND name IN ('log_write_time','log_writes')
                            """
                        )
                        rows = cursor.fetchall() or []
                        kv = {r[0]: float(r[1] or 0) for r in rows}
                        writes = kv.get('log_writes') or 0.0
                        write_time_us = kv.get('log_write_time') or 0.0
                        redo_ms = None
                        if writes > 0:
                            redo_ms = round((write_time_us / writes) / 1000.0, 2)
                        summary['perf']['redo_write_latency_ms'] = redo_ms
                    except Exception:
                        summary['perf']['redo_write_latency_ms'] = None
                conn.close()
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