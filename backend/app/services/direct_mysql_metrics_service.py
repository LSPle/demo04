import pymysql
import time
import logging
from typing import Dict, Any, Optional, Tuple
from ..models import Instance

logger = logging.getLogger(__name__)


class DirectMySQLMetricsService:
    """直接通过SQL查询获取MySQL性能指标，无需依赖Prometheus"""
    
    def __init__(self):
        self._last_status = {}
        self._last_timestamp = 0
    
    def _connect_to_mysql(self, inst: Instance) -> Optional[pymysql.Connection]:
        """建立MySQL连接"""
        try:
            # 添加调试日志
            logger.info(f"尝试连接MySQL: host={inst.host}, port={inst.port}, user={inst.username}, password={'***' if inst.password else 'None'}")
            
            conn = pymysql.connect(
                host=inst.host,
                port=inst.port,
                user=inst.username,
                password=inst.password,
                charset='utf8mb4',
                connect_timeout=10,
                read_timeout=30
            )
            logger.info(f"MySQL连接成功")
            return conn
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return None
    
    def _execute_query(self, conn: pymysql.Connection, query: str) -> Optional[Dict[str, Any]]:
        """执行SQL查询并返回结果"""
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return {'columns': columns, 'rows': rows}
        except Exception as e:
            logger.error(f"查询执行失败: {query}, 错误: {e}")
            return None
    
    def get_qps_tps_metrics(self, inst: Instance) -> Dict[str, Any]:
        """获取QPS和TPS指标"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'qps': None, 'tps': None, 'error': 'MySQL连接失败'}
        
        try:
            current_time = time.time()
            
            # 获取当前状态变量
            status_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Queries', 'Questions', 'Com_commit', 'Com_rollback',
                'Com_select', 'Com_insert', 'Com_update', 'Com_delete'
            )
            """
            
            result = self._execute_query(conn, status_query)
            if not result:
                return {'qps': None, 'tps': None, 'error': '状态查询失败'}
            
            # 解析状态变量
            current_status = {}
            for row in result['rows']:
                var_name, var_value = row
                current_status[var_name] = int(var_value) if var_value.isdigit() else 0
            
            # 计算QPS和TPS（需要两次采样的差值）
            qps = None
            tps = None
            
            if self._last_status and self._last_timestamp > 0:
                time_diff = current_time - self._last_timestamp
                if time_diff > 0:
                    # QPS = (当前Queries - 上次Queries) / 时间差
                    queries_diff = current_status.get('Queries', 0) - self._last_status.get('Queries', 0)
                    qps = round(queries_diff / time_diff, 2)
                    
                    # TPS = (当前事务数 - 上次事务数) / 时间差
                    current_transactions = current_status.get('Com_commit', 0) + current_status.get('Com_rollback', 0)
                    last_transactions = self._last_status.get('Com_commit', 0) + self._last_status.get('Com_rollback', 0)
                    transactions_diff = current_transactions - last_transactions
                    tps = round(transactions_diff / time_diff, 2)
            
            # 保存当前状态用于下次计算
            self._last_status = current_status.copy()
            self._last_timestamp = current_time
            
            return {
                'qps': qps,
                'tps': tps,
                'queries_total': current_status.get('Queries', 0),
                'transactions_total': current_status.get('Com_commit', 0) + current_status.get('Com_rollback', 0)
            }
            
        except Exception as e:
            logger.error(f"QPS/TPS指标获取失败: {e}")
            return {'qps': None, 'tps': None, 'error': str(e)}
        finally:
            conn.close()
    
    def get_performance_schema_metrics(self, inst: Instance) -> Dict[str, Any]:
        """从performance_schema获取性能指标"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'p95_latency_ms': None, 'avg_response_time_ms': None, 'error': 'MySQL连接失败'}
        
        try:
            # 检查performance_schema是否启用
            check_ps_query = "SELECT @@performance_schema"
            result = self._execute_query(conn, check_ps_query)
            if not result or not result['rows'] or result['rows'][0][0] != 1:
                return {
                    'p95_latency_ms': None,
                    'avg_response_time_ms': None,
                    'error': 'performance_schema未启用'
                }
            
            # 获取语句统计信息
            perf_query = """
            SELECT 
                ROUND(AVG(avg_timer_wait) / 1000000, 2) as avg_response_time_ms,
                COUNT(*) as statement_count,
                SUM(count_star) as total_executions
            FROM performance_schema.events_statements_summary_by_digest 
            WHERE last_seen > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            AND avg_timer_wait > 0
            """
            
            result = self._execute_query(conn, perf_query)
            if not result or not result['rows']:
                return {'p95_latency_ms': None, 'avg_response_time_ms': None, 'error': '性能数据不足'}
            
            row = result['rows'][0]
            avg_response_time_ms = row[0] if row[0] else None
            
            # 尝试获取P95延迟（使用MySQL兼容的方法）
            # 由于MySQL不支持PERCENTILE_CONT，使用近似计算方法
            p95_query = """
            SELECT 
                ROUND(avg_timer_wait / 1000000, 2) as latency_ms,
                count_star as execution_count
            FROM performance_schema.events_statements_summary_by_digest 
            WHERE last_seen > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            AND avg_timer_wait > 0
            ORDER BY avg_timer_wait DESC
            LIMIT 100
            """
            
            p95_result = self._execute_query(conn, p95_query)
            p95_latency_ms = None
            if p95_result and p95_result['rows']:
                # 简单取前5%的平均值作为P95近似值
                rows = p95_result['rows']
                if len(rows) > 0:
                    p95_index = max(1, int(len(rows) * 0.05))  # 取前5%
                    p95_latency_ms = sum(row[0] for row in rows[:p95_index]) / p95_index
            
            return {
                'p95_latency_ms': p95_latency_ms,
                'avg_response_time_ms': avg_response_time_ms,
                'statement_count': row[1] if len(row) > 1 else None,
                'total_executions': row[2] if len(row) > 2 else None
            }
            
        except Exception as e:
            logger.error(f"Performance Schema指标获取失败: {e}")
            return {'p95_latency_ms': None, 'avg_response_time_ms': None, 'error': str(e)}
        finally:
            conn.close()
    
    def get_slow_query_metrics(self, inst: Instance) -> Dict[str, Any]:
        """获取慢查询相关指标"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'slow_query_ratio': None, 'slow_queries_total': None, 'error': 'MySQL连接失败'}
        
        try:
            # 获取慢查询统计
            slow_query_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Slow_queries', 'Queries'
            )
            """
            
            result = self._execute_query(conn, slow_query_query)
            if not result:
                return {'slow_query_ratio': None, 'slow_queries_total': None, 'error': '慢查询统计获取失败'}
            
            status_vars = {}
            for row in result['rows']:
                var_name, var_value = row
                status_vars[var_name] = int(var_value) if var_value.isdigit() else 0
            
            slow_queries = status_vars.get('Slow_queries', 0)
            total_queries = status_vars.get('Queries', 0)
            
            # 计算慢查询比例
            slow_query_ratio = None
            if total_queries > 0:
                slow_query_ratio = round((slow_queries / total_queries) * 100, 4)
            
            return {
                'slow_query_ratio': slow_query_ratio,
                'slow_queries_total': slow_queries,
                'total_queries': total_queries
            }
            
        except Exception as e:
            logger.error(f"慢查询指标获取失败: {e}")
            return {'slow_query_ratio': None, 'slow_queries_total': None, 'error': str(e)}
        finally:
            conn.close()
    
    def get_index_usage_metrics(self, inst: Instance) -> Dict[str, Any]:
        """获取索引使用率指标"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'index_usage_rate': None, 'error': 'MySQL连接失败'}
        
        try:
            # 获取索引使用相关的状态变量
            index_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Handler_read_key', 'Handler_read_next', 'Handler_read_prev',
                'Handler_read_first', 'Handler_read_last', 'Handler_read_rnd',
                'Handler_read_rnd_next'
            )
            """
            
            result = self._execute_query(conn, index_query)
            if not result:
                return {'index_usage_rate': None, 'error': '索引统计获取失败'}
            
            status_vars = {}
            for row in result['rows']:
                var_name, var_value = row
                status_vars[var_name] = int(var_value) if var_value.isdigit() else 0
            
            # 计算索引使用率
            # 索引读取 = Handler_read_key + Handler_read_next + Handler_read_prev + Handler_read_first + Handler_read_last
            index_reads = (
                status_vars.get('Handler_read_key', 0) +
                status_vars.get('Handler_read_next', 0) +
                status_vars.get('Handler_read_prev', 0) +
                status_vars.get('Handler_read_first', 0) +
                status_vars.get('Handler_read_last', 0)
            )
            
            # 全表扫描 = Handler_read_rnd + Handler_read_rnd_next
            table_scans = (
                status_vars.get('Handler_read_rnd', 0) +
                status_vars.get('Handler_read_rnd_next', 0)
            )
            
            total_reads = index_reads + table_scans
            index_usage_rate = None
            
            if total_reads > 0:
                index_usage_rate = round((index_reads / total_reads) * 100, 2)
            
            return {
                'index_usage_rate': index_usage_rate,
                'index_reads': index_reads,
                'table_scans': table_scans,
                'total_reads': total_reads
            }
            
        except Exception as e:
            logger.error(f"索引使用率指标获取失败: {e}")
            return {'index_usage_rate': None, 'error': str(e)}
        finally:
            conn.close()
    
    def get_basic_status_metrics(self, inst: Instance) -> Dict[str, Any]:
        """获取MySQL基础状态指标"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'threads_connected': None, 'threads_running': None, 'error': 'MySQL连接失败'}
        
        try:
            # 获取基础状态变量
            status_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Threads_connected', 'Threads_running',
                'Innodb_row_lock_waits', 'Innodb_row_lock_time',
                'Innodb_buffer_pool_read_requests', 'Innodb_buffer_pool_reads'
            )
            """
            
            result = self._execute_query(conn, status_query)
            if not result:
                return {'threads_connected': None, 'threads_running': None, 'error': '状态查询失败'}
            
            # 解析状态变量
            status_vars = {}
            for row in result['rows']:
                var_name, var_value = row
                status_vars[var_name] = int(var_value) if var_value.isdigit() else 0
            
            # 计算缓存命中率
            cache_hit_rate = None
            try:
                req = float(status_vars.get('Innodb_buffer_pool_read_requests', 0))
                rd = float(status_vars.get('Innodb_buffer_pool_reads', 0))
                if req > 0:
                    ratio = 1.0 - (rd / req)
                    ratio = max(0.0, min(1.0, ratio))
                    cache_hit_rate = round(ratio * 100.0, 2)
            except Exception:
                cache_hit_rate = None
            
            # 获取死锁计数
            deadlocks = None
            try:
                deadlock_query = """
                SELECT COALESCE(MAX(`count`),0)
                FROM information_schema.innodb_metrics
                WHERE name='lock_deadlocks' AND status='enabled'
                """
                deadlock_result = self._execute_query(conn, deadlock_query)
                if deadlock_result and deadlock_result['rows']:
                    deadlocks = int(deadlock_result['rows'][0][0] or 0)
            except Exception:
                deadlocks = None
            
            # 获取Redo写入延迟
            redo_write_latency_ms = None
            try:
                redo_query = """
                SELECT name, `count` FROM information_schema.innodb_metrics
                WHERE status='enabled' AND name IN ('log_write_time','log_writes')
                """
                redo_result = self._execute_query(conn, redo_query)
                if redo_result and redo_result['rows']:
                    kv = {r[0]: float(r[1] or 0) for r in redo_result['rows']}
                    writes = kv.get('log_writes', 0.0)
                    write_time_us = kv.get('log_write_time', 0.0)
                    if writes > 0:
                        redo_write_latency_ms = round((write_time_us / writes) / 1000.0, 2)
            except Exception:
                redo_write_latency_ms = None
            
            return {
                'threads_connected': status_vars.get('Threads_connected'),
                'threads_running': status_vars.get('Threads_running'),
                'innodb_row_lock_waits': status_vars.get('Innodb_row_lock_waits'),
                'innodb_row_lock_time_ms': status_vars.get('Innodb_row_lock_time'),
                'cache_hit_rate': cache_hit_rate,
                'deadlocks': deadlocks,
                'redo_write_latency_ms': redo_write_latency_ms
            }
            
        except Exception as e:
            logger.error(f"基础状态指标获取失败: {e}")
            return {'threads_connected': None, 'threads_running': None, 'error': str(e)}
        finally:
            conn.close()
    
    def get_all_direct_metrics(self, inst: Instance) -> Dict[str, Any]:
        """获取所有直接查询的MySQL指标"""
        metrics = {
            'generated_at': int(time.time()),
            'source': 'direct_mysql_query'
        }
        
        # 获取基础状态指标
        basic_metrics = self.get_basic_status_metrics(inst)
        metrics.update(basic_metrics)
        
        # 获取QPS/TPS指标
        qps_tps = self.get_qps_tps_metrics(inst)
        metrics.update(qps_tps)
        
        # 获取性能指标
        perf_metrics = self.get_performance_schema_metrics(inst)
        metrics.update(perf_metrics)
        
        # 获取慢查询指标
        slow_metrics = self.get_slow_query_metrics(inst)
        metrics.update(slow_metrics)
        
        # 获取索引使用率
        index_metrics = self.get_index_usage_metrics(inst)
        metrics.update(index_metrics)
        
        return metrics


# 全局实例
direct_mysql_metrics_service = DirectMySQLMetricsService()