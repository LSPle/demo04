
import pymysql
import time
import logging
from typing import Dict, Any, Optional, Tuple
from ..models import Instance

logger = logging.getLogger(__name__)
# 元组访问比字典访问 更快

#直接通过SQL查询获取MySQL性能指标，无需依赖Prometheus
class DirectMySQLMetricsService:
   
    def __init__(self):
        pass
    #建立MySQL连接"
    def _connect_to_mysql(self, inst: Instance):
       
        try:                     
            conn = pymysql.connect(
                host=inst.host,
                port=inst.port,
                user=inst.username,
                password=inst.password,
                charset='utf8mb4',
                connect_timeout=10,
                read_timeout=30
            )
            return conn
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return None
    #执行SQL查询并返回结果
    def execute_query(self, conn: pymysql.Connection, query: str):       
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return {'columns': columns, 'rows': rows}
        except Exception as e:
            logger.error(f"查询执行失败: {query}, 错误: {e}")
            return None

    #在一次调用中完成两次采样，按窗口秒数计算 QPS/TPS
    def get_qps_tps_window(self, inst: Instance, window_s: int = 6):
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'qps': None, 'tps': None, 'error': 'MySQL连接失败'}
        try:
            status_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Queries', 'Com_commit', 'Com_rollback'
            )
            """
            # 第一次采样
            t0 = time.time()
            r1 = self.execute_query(conn, status_query)
            if not r1 or not r1.get('rows'):
                return {'qps': None, 'tps': None, 'error': '状态查询失败'}
            s1: Dict[str, int] = {}
            for row in r1['rows']:
                name = row[0]
                val = row[1]
                try:
                    s1[name] = int(val) if (val is not None and str(val).isdigit()) else 0
                except Exception:
                    s1[name] = 0
            # 睡眠窗口秒数
            # try:
            #     sleep_seconds = max(1, int(window_s))
            # except Exception:
            #     sleep_seconds = 6
            time.sleep(6)
            # 第二次采样
            t1 = time.time()
            r2 = self.execute_query(conn, status_query)
            if not r2 or not r2.get('rows'):
                return {'qps': None, 'tps': None, 'error': '状态查询失败'}
            s2: Dict[str, int] = {}
            for row in r2['rows']:
                name = row[0]
                val = row[1]
                try:
                    s2[name] = int(val) if (val is not None and str(val).isdigit()) else 0
                except Exception:
                    s2[name] = 0
            # 计算差值与速率
            dt = max(1e-3, t1 - t0)
            queries_diff = max(0, s2.get('Queries', 0) - s1.get('Queries', 0))
            trx2 = s2.get('Com_commit', 0) + s2.get('Com_rollback', 0)
            trx1 = s1.get('Com_commit', 0) + s1.get('Com_rollback', 0)
            tps_diff = max(0, trx2 - trx1)
            qps = round(queries_diff / dt, 2)
            tps = round(tps_diff / dt, 2)
            return {
                'qps': qps,
                'tps': tps,
                'queries_total': s2.get('Queries', 0),
                'transactions_total': trx2
            }
        except Exception as e:
            logger.info(f"窗口采样失败: {e}")
            return {'qps': None, 'tps': None, 'error': str(e)}
        finally:         
            conn.close()
 
    #从performance_schema获取 性能指标
    def get_performance_schema_metrics(self, inst: Instance):
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'p95_latency_ms': None, 'avg_response_time_ms': None, 'error': 'MySQL连接失败'}        
        try:
            # 检查performance_schema是否启用
            check_ps_query = "SELECT @@performance_schema"
            result = self.execute_query(conn, check_ps_query)
            
            # 简化判断：如果查询失败或结果不是1，说明未启用
            if not result or result['rows'][0][0] != 1:
                return {
                    'p95_latency_ms': None,
                    'avg_response_time_ms': None,
                    'error': 'performance_schema未启用'
                }
                     
                     
            # 性能统计信息
            # 请帮我从数据库的‘SQL性能统计表’里，查一下在最近5分钟内，所有活跃过的SQL语句的总体表现：           
            # 它们的平均执行时间是多少毫秒？（方便我判断数据库快还是慢）
            # 总共有多少种不同类型的SQL语句？（看看业务复杂度）
            # 这些SQL语句加起来一共被执行了多少次？（看看负载压力）

            perf_query = """
            SELECT 
                ROUND(AVG(avg_timer_wait) / 1000000, 2) as avg_response_time_ms,
                COUNT(*) as statement_count,
                SUM(count_star) as total_executions
            FROM performance_schema.events_statements_summary_by_digest 
            WHERE last_seen > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            AND avg_timer_wait > 0  
            """
            
            result = self.execute_query(conn, perf_query)
            if not result or not result['rows']:
                return {'p95_latency_ms': None, 'avg_response_time_ms': None, 'error': '性能数据不足'}

            logger.info(f"Performance 查询返回{result['rows']}")
            # avg_response_time_ms = result['rows'][0][0]
            
            # 尝试获取P95延迟（使用MySQL兼容的方法）
            # 由于MySQL不支持PERCENTILE_CONT，使用近似计算方法

            # 请帮我找出在最近5分钟内，执行时间最长的100个SQL语句，并显示它们各自的平均执行时间和总执行次数
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
            
            p95_result = self.execute_query(conn, p95_query)
            '''查看数据'''
            logger.info(f"Performance P95 查询返回{p95_result}")
            p95_latency_ms = None
            slowest_query_ms = None
            if p95_result and p95_result['rows']:
                # 简单取前5%的平均值作为P95近似值
                rows = p95_result['rows']
                if len(rows) > 0:
                    p95_index = max(1, int(len(rows) * 0.05))  # 取前5%
                    p95_latency_ms = sum(row[0] for row in rows[:p95_index]) / p95_index
                    # 记录最慢查询的平均延迟（按avg_timer_wait降序）
                    try:
                        slowest_query_ms = float(rows[0][0] or 0)
                    except Exception:
                        slowest_query_ms = None
            
            # 获取第一个查询的完整结果
            first_row = result['rows'][0]
            '''查看数据'''
            logger.info(f"Performance 第一个查询返回{first_row}")
            return {
                'p95_latency_ms': p95_latency_ms,
                'avg_response_time_ms': first_row[0],
                'statement_count': first_row[1],
                'total_executions': first_row[2],
                'slowest_query_ms': slowest_query_ms
            }
            
        except Exception as e:
            logger.error(f"Performance Schema指标获取失败: {e}")
            return {'p95_latency_ms': None, 'avg_response_time_ms': None, 'error': str(e)}
        finally:
            conn.close()
    
    #获取慢查询相关指标
    def get_slow_query_metrics(self, inst: Instance):
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'slow_query_ratio': None, 'slow_queries_total': None, 'error': 'MySQL连接失败'}    
        # 获取慢查询统计  
        try:            
            slow_query_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Slow_queries', 'Queries'
            )
            """            
            result = self.execute_query(conn, slow_query_query)

            # logger.info(f"慢查询查询返回{result}")
            

            # if not result:
            #     return {'slow_query_ratio': None, 'slow_queries_total': None, 'error': '慢查询统计获取失败'}
            
            status_vars = {}
            for row in result['rows']:
                var_name = row[0]
                var_value = row[1]
                if var_value.isdigit():
                    status_vars[var_name] = int(var_value)
                else:
                    status_vars[var_name] = 0
                
            
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
    #获取索引使用率指标
    def get_index_usage_metrics(self, inst: Instance):
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'index_usage_rate': None, 'error': 'MySQL连接失败'}
         # 获取索引使用相关的状态变量
        """
        Handler_read_key - 基于索引键读取行的次数（高=索引使用良好）

        Handler_read_next - 按索引顺序读下一行的次数
        
        Handler_read_prev - 按索引顺序读前一行的次数
        
        Handler_read_first - 读索引第一个条目的次数
        
        Handler_read_last - 读索引最后一个条目的次数
        
        Handler_read_rnd - 根据固定位置读行的次数
        
        Handler_read_rnd_next - 读数据文件下一行的次数（高=全表扫描多）
        """
        try:         
            index_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Handler_read_key', 'Handler_read_next', 'Handler_read_prev',
                'Handler_read_first', 'Handler_read_last', 'Handler_read_rnd',
                'Handler_read_rnd_next'
            )
            """        
            result = self.execute_query(conn, index_query)
            # if not result:
            #     return {'index_usage_rate': None, 'error': '索引统计获取失败'}
            
            status_vars = {}
            for row in result['rows']:
                var_name = row[0]
                var_value = row[1]
                if var_value.isdigit():
                    status_vars[var_name] = int(var_value)
                else:
                    status_vars[var_name] = 0            
            
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
    #获取MySQL基础状态指标
    def get_basic_status_metrics(self, inst: Instance):
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'threads_connected': None, 'threads_running': None, 'error': 'MySQL连接失败'}
        """
        连接相关:
        Threads_connected：当前已建立的客户端连接数       
        Threads_running：当前正在执行查询的线程数（活跃连接）     
        Max_used_connections：MySQL 启动以来同时使用的最大连接数
        
        InnoDB 行锁相关:
        Innodb_row_lock_waits：发生行锁等待的次数  
        Innodb_row_lock_time：行锁等待的总时间（毫秒）
        
        缓冲池性能相关:
        Innodb_buffer_pool_read_requests：InnoDB 缓冲池的读请求次数    
        Innodb_buffer_pool_reads：从磁盘读取页面的次数（未命中缓冲池）
        """
        try:
            # 获取基础状态变量
            status_query = """
            SHOW GLOBAL STATUS WHERE Variable_name IN (
                'Threads_connected', 'Threads_running',
                'Innodb_row_lock_waits', 'Innodb_row_lock_time',
                'Innodb_buffer_pool_read_requests', 'Innodb_buffer_pool_reads',
                'Max_used_connections'
            )
            """
            
            result = self.execute_query(conn, status_query)
            if not result:
                return {'threads_connected': None, 'threads_running': None, 'error': '状态查询失败'}
            
            # 解析状态变量
            status_vars = {}
            for row in result['rows']:
                var_name, var_value = row
                if var_value.isdigit():
                    status_vars[var_name] = int(var_value)
                else:
                    status_vars[var_name] = 0
            
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
                deadlock_result = self.execute_query(conn, deadlock_query)
                if deadlock_result and deadlock_result['rows']:
                    deadlocks = int(deadlock_result['rows'][0][0] or 0)
            except Exception:
                deadlocks = None
            
            # 获取Redo写入延迟
            redo_write_latency_ms = None
            # A: 优先尝试 MySQL 8.0 的 SHOW GLOBAL STATUS 口径
            try:
                status_redo_query = """
                SHOW GLOBAL STATUS WHERE Variable_name IN (
                    'Innodb_redo_log_write_time','Innodb_redo_log_writes'
                )
                """
                sres = self.execute_query(conn, status_redo_query)
                if sres and sres['rows']:
                    kv = {row[0]: float(row[1] or 0) for row in sres['rows']}
                    writes = kv.get('Innodb_redo_log_writes', 0.0)
                    write_time_us = kv.get('Innodb_redo_log_write_time', 0.0)
                    if writes and writes > 0 and write_time_us and write_time_us > 0:
                        redo_write_latency_ms = round((write_time_us / writes) / 1000.0, 3)
            except Exception:
                pass

            # B: 次选使用 information_schema.innodb_metrics 的写入时间
            if redo_write_latency_ms is None:
                try:
                    redo_query = """
                    SELECT name, `count` FROM information_schema.innodb_metrics
                    WHERE status='enabled' AND name IN ('log_write_time','log_writes')
                    """
                    redo_result = self.execute_query(conn, redo_query)
                    if redo_result and redo_result['rows']:
                        kv = {r[0]: float(r[1] or 0) for r in redo_result['rows']}
                        writes = kv.get('log_writes', 0.0)
                        write_time_us = kv.get('log_write_time', 0.0)
                        if writes and writes > 0 and write_time_us and write_time_us > 0:
                            redo_write_latency_ms = round((write_time_us / writes) / 1000.0, 3)
                except Exception:
                    pass

            # C: 再次回退为 flush 时间近似值（若存在）
            if redo_write_latency_ms is None:
                try:
                    flush_query = """
                    SELECT name, `count` FROM information_schema.innodb_metrics
                    WHERE status='enabled' AND name IN ('log_flush_total_time','log_writes')
                    """
                    fres = self.execute_query(conn, flush_query)
                    if fres and fres['rows']:
                        kv = {r[0]: float(r[1] or 0) for r in fres['rows']}
                        writes = kv.get('log_writes', 0.0)
                        flush_time_us = kv.get('log_flush_total_time', 0.0)
                        if writes and writes > 0 and flush_time_us and flush_time_us > 0:
                            redo_write_latency_ms = round((flush_time_us / writes) / 1000.0, 3)
                except Exception:
                    pass
            
            return {
                'threads_connected': status_vars.get('Threads_connected'),
                'threads_running': status_vars.get('Threads_running'),
                'innodb_row_lock_waits': status_vars.get('Innodb_row_lock_waits'),
                'innodb_row_lock_time_ms': status_vars.get('Innodb_row_lock_time'),
                'cache_hit_rate': cache_hit_rate,
                'deadlocks': deadlocks,
                'redo_write_latency_ms': redo_write_latency_ms,
                'peak_connections': status_vars.get('Max_used_connections')
            }
            
        except Exception as e:
            logger.error(f"基础状态指标获取失败: {e}")
            return {'threads_connected': None, 'threads_running': None, 'error': str(e)}
        finally:
            conn.close()
    '''获取所有直接查询的MySQL指标'''
    def get_all_direct_metrics(self, inst: Instance):
        metrics = {
            'generated_at': int(time.time()),
            
        }
        # 从metrics删除'source': 'direct_ysql_query'
        # 获取基础状态指标
        basic_metrics = self.get_basic_status_metrics(inst)
        metrics.update(basic_metrics)
        
        # QPS/TPS 指标在通过窗口采样
        
        # 获取性能指标
        perf_metrics = self.get_performance_schema_metrics(inst)
        metrics.update(perf_metrics)
        
        # 获取慢查询指标
        slow_metrics = self.get_slow_query_metrics(inst)
        metrics.update(slow_metrics)
        
        # 获取索引使用率
        index_metrics = self.get_index_usage_metrics(inst)
        metrics.update(index_metrics)

        # 新增：最大连接数
        try:
            extra_max = self.get_variable_max_connections(inst)
            if isinstance(extra_max, dict):
                metrics.update(extra_max)
        except Exception:
            pass

        # 新增：主从延迟（毫秒）
        try:
            repl = self.get_replication_metrics(inst)
            if isinstance(repl, dict):
                metrics.update(repl)
        except Exception:
            pass
        
        return metrics
    """查询最大连接数。"""
    def get_variable_max_connections(self, inst: Instance):
        """获取MySQL max_connections配置变量"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'max_connections': None, 'error': 'MySQL连接失败'}
        
        try:
            # result = self.execute_query(conn, 'SELECT @@max_connections')
            # if not result or not result.get('rows'):
            #     return {'max_connections': None, 'error': '配置查询失败'}
            connections_query = """
            SELECT @@max_connections
            """
            result = self.execute_query(conn, connections_query)
            if not result or not result.get('rows'):
                return {'max_connections': None, 'error': '配置查询失败'}
            
            row = result['rows'][0]
            if row and len(row) > 0:
                try:
                    val = int(row[0])
                    return {'max_connections': val}
                except (ValueError, TypeError):
                    # logger.error(f"max_connections值解析失败: {row[0]}")
                    return {'max_connections': None, 'error': '配置值解析失败'}
            
            return {'max_connections': None, 'error': '未获取到配置值'}
            
        except Exception as e:
            logger.error(f"获取max_connections失败: {e}")
            return {'max_connections': None, 'error': str(e)}
        finally:
            conn.close()
            
    def get_replication_metrics(self, inst: Instance):
        """获取MySQL主从复制延迟指标"""
        conn = self._connect_to_mysql(inst)
        if not conn:
            return {'replication_delay_ms': None, 'error': 'MySQL连接失败'}
        
        try:
            delay_ms = None
            # 尝试不同的复制状态查询（兼容不同MySQL版本）
            replication_queries = ['SHOW SLAVE STATUS', 'SHOW REPLICA STATUS']
            
            for query in replication_queries:
                try:
                    result = self.execute_query(conn, query)
                    if result and result.get('rows') and len(result['rows']) > 0:
                        # 获取列名索引
                        columns = result.get('columns', [])
                        row = result['rows'][0]
                        
                        # 构建字典便于查找
                        row_dict = {}
                        for i, col in enumerate(columns):
                            if i < len(row):
                                row_dict[col] = row[i]
                        
                        # 查找延迟字段
                        sec = row_dict.get('Seconds_Behind_Master')
                        if sec is None:
                            sec = row_dict.get('Seconds_Behind_Source')
                        
                        if sec is not None:
                            try:
                                delay_ms = int(float(sec)) * 1000
                                break
                            except (ValueError, TypeError):
                                logger.error(f"复制延迟值解析失败: {sec}")
                                continue
                except Exception as e:
                    # 尝试下一个查询
                    logger.debug(f"复制状态查询失败: {query}, 错误: {e}")
                    continue
            
            return {'replication_delay_ms': delay_ms}
            
        except Exception as e:
            logger.error(f"获取复制指标失败: {e}")
            return {'replication_delay_ms': None, 'error': str(e)}
        finally:
            conn.close()


# 全局实例
direct_mysql_metrics_service = DirectMySQLMetricsService()
