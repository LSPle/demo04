import logging
import re
import datetime
from typing import Any, Dict, List, Tuple, Optional

try:
    import pymysql
except ImportError:
    pymysql = None


from ..models import Instance

'''
  慢查询日志分析服务
'''
logger = logging.getLogger(__name__)


# 将时间值转换为秒数（简化版本）
def _sec(val):
    """
    将时间值转换为秒数
    参数: val - 可能是时间差对象、数字或None
    返回: 浮点数秒数
    """
    if val is None:
        return 0.0
    
    # 如果是时间差对象（如datetime.timedelta）
    if hasattr(val, 'total_seconds'):
        return float(val.total_seconds())
    
    # 如果是数字，直接转换
    try:
        return float(val)
    except:
        return 0.0

# 将各种类型的值转换为字符串
def to_string(val):
    """
    将各种类型的值转换为字符串，用于JSON序列化
    参数: val - 任意类型的值
    返回: 字符串
    """
    if val is None:
        return ''
    
    # 如果是日期时间对象，格式化为字符串
    if isinstance(val, datetime.datetime):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    
    # 如果是字节类型，解码为字符串
    if isinstance(val, (bytes, bytearray)):
        return val.decode('utf-8', errors='ignore')
    
    # 其他类型直接转换为字符串
    return str(val)

#MySQL慢查询日志分析服务
class SlowLogService:
 
    #初始化慢查询服务
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _connect(self, inst: Instance):     
        if not pymysql:
            raise RuntimeError("MySQL驱动不可用")
        
        return pymysql.connect(
            host=inst.host,
            port=inst.port,
            user=inst.username or '',
            password=inst.password or '',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            write_timeout=self.timeout
        )

    #分析MySQL慢查询日志
    def analyze(self, inst: Instance, top: int = 20, min_avg_ms: int = 10, tail_kb: int = 256):

        # 基本参数检查
        if not inst:
            return False, {}, "实例不存在"
        if (inst.db_type or '').strip() != 'MySQL':
            return False, {}, "仅支持MySQL实例"
        
        try:
            conn = self._connect(inst)
            try:
                # 初始化返回数据结构
                overview = {}
                ps_top = []
                file_samples = []
                warnings = []

                with conn.cursor() as cur:
                    # 1. 获取MySQL慢查询相关配置
                    overview = self._get_mysql_config(cur)
                    
                    # 2. 从performance_schema获取Top SQL统计
                    if overview.get('performance_schema') == 'ON':
                        ps_top = self._get_top_sql_from_ps(cur, top, min_avg_ms)
                    else:
                        warnings.append('performance_schema 未开启，无法生成 Top SQL 指纹统计')

                    # 3. 从慢查询表获取样本数据
                    if overview.get('slow_query_log') == 'ON' and 'TABLE' in overview.get('log_output', ''):
                        file_samples = self._get_samples_from_table(cur)
                    else:
                        warnings.append('慢查询日志未以TABLE方式输出，跳过表抽样')

                # 组装返回数据
                data = {
                    'overview': overview,
                    'ps_top': ps_top,
                    'file_samples': file_samples,
                    'warnings': warnings
                }
                return True, data, 'OK'
                
            finally:
                conn.close()
                
        except pymysql.Error as db_error:
            # 数据库连接或查询错误
            error_msg = f"数据库操作失败: {db_error}"
            logger.error(f"慢日志分析失败(实例ID={getattr(inst, 'id', None)}): {error_msg}")
            return False, {}, error_msg
        except Exception as e:
            # 其他未预期的错误
            error_msg = f"系统错误: {e}"
            logger.error(f"慢日志分析失败(实例ID={getattr(inst, 'id', None)}): {error_msg}")
            return False, {}, error_msg
    #获取MySQL慢查询相关配置
    def _get_mysql_config(self, cur):
       
        cur.execute("""
            SHOW GLOBAL VARIABLES WHERE Variable_name IN (
              'performance_schema', 'long_query_time', 'slow_query_log', 'log_output', 'slow_query_log_file'
            )
        """)
        # 获取查询结果，如果为空则使用空列表
        rows = cur.fetchall() or []
        vars_map = {}
        for row in rows:
            variable_name = row['Variable_name']
            variable_value = row['Value']
            vars_map[variable_name] = variable_value

        # 统一慢查询日志格式
        ps_raw = str(vars_map.get('performance_schema', '')).strip().lower()
        performance_schema_on = ps_raw in ('1', 'on', 'yes', 'true')

        slow_raw = str(vars_map.get('slow_query_log', '')).strip().lower()
        slow_query_log = slow_raw in ('1', 'on', 'yes', 'true')

        long_query_time = vars_map.get('long_query_time')
        log_output_raw = str(vars_map.get('log_output') or '')
        slow_file = str(vars_map.get('slow_query_log_file') or '').strip()

        return {
            'performance_schema': 'ON' if performance_schema_on else 'OFF',
            'slow_query_log': 'ON' if slow_query_log else 'OFF',
            'long_query_time': float(long_query_time) if str(long_query_time).replace('.', '', 1).isdigit() else long_query_time,
            'log_output': log_output_raw,
            'slow_query_log_file': slow_file or ''
        }
    
    #从performance_schema获取Top SQL统计
    def _get_top_sql_from_ps(self, cur, top: int, min_avg_ms: int):
        # 使用较低的阈值以获取更多有价值的数据
        effective_min_ms = max(0.5, min_avg_ms * 0.1)
        #找出拖慢数据库的慢 SQL
        sql = """
            SELECT schema_name, digest, digest_text, count_star,
                   sum_timer_wait, sum_rows_examined, sum_rows_sent
            FROM performance_schema.events_statements_summary_by_digest
            WHERE (schema_name IS NULL OR schema_name NOT IN ('mysql','sys','information_schema'))
              AND sum_timer_wait >= (%s * 1000000000) * GREATEST(count_star, 1)
              AND count_star > 0
            ORDER BY (sum_timer_wait / GREATEST(count_star, 1)) DESC LIMIT %s
        """
        
        try:
            cur.execute(sql, (int(effective_min_ms), int(top)))
            rows = cur.fetchall() or []
        except Exception:
            return []

        top_list = []
        for r in rows:
            cnt = int(r.get('count_star') or 0)
            avg_ms, total_ms = self._calculate_timing(r.get('sum_timer_wait'), cnt)
            
            rows_examined = int(r.get('sum_rows_examined') or 0)
            rows_sent = int(r.get('sum_rows_sent') or 0)
            re_avg = (rows_examined / cnt) if cnt else 0.0
            rs_avg = (rows_sent / cnt) if cnt else 0.0
            
            top_list.append({
                'schema': r.get('schema_name') or '',
                'digest': r.get('digest') or '',
                'query': (r.get('digest_text') or '')[:500],
                'count': cnt,
                'avg_latency_ms': round(avg_ms, 2),
                'total_latency_ms': round(total_ms, 2),
                'rows_examined_avg': round(re_avg, 1),
                'rows_sent_avg': round(rs_avg, 1),
            })
        return top_list
    #计算平均和总执行时间
    def _calculate_timing(self, timer_ps, cnt: int):
        try:
            ps = int(timer_ps)
            total_ms = ps / 1_000_000_000.0  # 转换为毫秒
        except Exception:
            return 0.0, 0.0
        
        avg_ms = (total_ms / cnt) if cnt else 0.0
        return avg_ms, total_ms
    #从mysql.slow_log表获取样本数据
    def _get_samples_from_table(self, cur):
 
        try:
            cur.execute(
                "SELECT start_time, db, query_time, lock_time, rows_sent, rows_examined, sql_text "
                "FROM mysql.slow_log ORDER BY start_time DESC LIMIT %s",
                (10,)  # 获取最近10条记录
            )
            rows = cur.fetchall() or []

            samples = []
            for r in rows:
                samples.append({
                    'time': to_string(r.get('start_time')),
                    'db': to_string(r.get('db')),
                    'query_time_ms': round(_sec(r.get('query_time')) * 1000, 2),
                    'lock_time_ms': round(_sec(r.get('lock_time')) * 1000, 2),
                    'rows_sent': int(r.get('rows_sent') or 0),
                    'rows_examined': int(r.get('rows_examined') or 0),
                    'sql': to_string(r.get('sql_text'))
                })
            return samples
            
        except Exception as e:
            # 读取慢日志表抽样数据失败，返回空列表
            logger.info(f"读取慢日志表抽样失败: {e}")
            return []
    #降低阈值到0.5ms(演示用)
    def _collect_ps_top(self, cur, top: int, min_avg_ms: int):
        effective_min_ms = max(0.5, min_avg_ms * 0.1)  # 使用更低的阈值
        sql = (
            "SELECT schema_name, digest, digest_text, count_star, "
            "       sum_timer_wait, sum_rows_examined, sum_rows_sent "
            "  FROM performance_schema.events_statements_summary_by_digest "
            " WHERE (schema_name IS NULL OR schema_name NOT IN ('mysql','sys','information_schema')) "
            "   AND sum_timer_wait >= (%s * 1000000000) * GREATEST(count_star, 1) "
            "   AND count_star > 0 "
            " ORDER BY (sum_timer_wait / GREATEST(count_star, 1)) DESC LIMIT %s"
        )
        try:
            cur.execute(sql, (int(effective_min_ms), int(top)))
            rows = cur.fetchall() or []
        except Exception:
            # 某些MySQL版本字段名不同或performance_schema表不可用，返回空列表
            return []

        def _ps_to_ms(timer_ps: Any, cnt: int) -> Tuple[float, float]:
            try:
                ps = int(timer_ps)
                total_ms = ps / 1_000_000_000.0  # 1e12 ps = 1s; 1e9 ps = 1ms
            except Exception:
                # 时间转换失败，返回默认值0
                return 0.0, 0.0
            avg_ms = (total_ms / cnt) if cnt else 0.0
            return avg_ms, total_ms

        top_list: List[Dict[str, Any]] = []
        for r in rows:
            cnt = int(r.get('count_star') or 0)
            avg_ms, total_ms = _ps_to_ms(r.get('sum_timer_wait'), cnt)
            rows_examined = int(r.get('sum_rows_examined') or 0)
            rows_sent = int(r.get('sum_rows_sent') or 0)
            re_avg = (rows_examined / cnt) if cnt else 0.0
            rs_avg = (rows_sent / cnt) if cnt else 0.0
            top_list.append({
                'schema': r.get('schema_name') or '',
                'digest': r.get('digest') or '',
                'query': (r.get('digest_text') or '')[:500],
                'count': cnt,
                'avg_latency_ms': round(avg_ms, 2),
                'total_latency_ms': round(total_ms, 2),
                'rows_examined_avg': round(re_avg, 1),
                'rows_sent_avg': round(rs_avg, 1),
            })
        return top_list

    # 从mysql.slow_log表分页查询慢查询记录
    def list_from_table(
        self,
        inst: Instance,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None):
        # 基本参数检查
        if not inst:
            return False, {}, "实例不存在"
        if (inst.db_type or '').strip() != 'MySQL':
            return False, {}, "仅支持MySQL实例"
            
        try:
            conn = self._connect(inst)
            try:
                with conn.cursor() as cur:
                    # 检查慢查询日志配置
                    overview = self._check_slow_log_config(cur)
                    if not self._is_table_output_enabled(overview):
                        return False, {'overview': overview}, "仅支持 log_output 包含 TABLE 的数据库"

                    # 构建查询条件
                    where_sql, params = self._build_query_conditions(filters or {})

                    # 获取总记录数
                    total = self._get_total_count(cur, where_sql, params)

                    # 处理分页参数
                    page = max(1, int(page)) if str(page).isdigit() else 1
                    page_size = max(1, min(100, int(page_size))) if str(page_size).isdigit() else 10
                    offset = (page - 1) * page_size

                    # 获取分页数据
                    items = self._get_paged_data(cur, where_sql, params, page_size, offset)

                    data = {
                        'overview': overview,
                        'items': items,
                        'total': total,
                        'page': page,
                        'page_size': page_size,
                    }
                    return True, data, 'OK'
                    
            finally:
                conn.close()
                
        except pymysql.Error as db_error:
            # 数据库连接或查询错误
            error_msg = f"数据库操作失败: {db_error}"
            logger.error(f"查询慢日志表失败(实例ID={getattr(inst, 'id', None)}): {error_msg}")
            return False, {}, error_msg
        except Exception as e:
            # 其他未预期的错误
            error_msg = f"系统错误: {e}"
            logger.error(f"查询慢日志表失败(实例ID={getattr(inst, 'id', None)}): {error_msg}")
            return False, {}, error_msg
    #检查慢查询日志配置
    def _check_slow_log_config(self, cur):
        
        cur.execute(
            "SHOW GLOBAL VARIABLES WHERE Variable_name IN ('slow_query_log','log_output')"
        )
        rows = cur.fetchall() or []
        vars_map = {r['Variable_name']: r['Value'] for r in rows}
        
        return {
            'slow_query_log': str(vars_map.get('slow_query_log') or ''),
            'log_output': str(vars_map.get('log_output') or ''),
        }
    #检查是否启用了TABLE输出
    def _is_table_output_enabled(self, overview):
        log_output = overview.get('log_output', '').strip().upper()
        return any(p.strip() == 'TABLE' for p in log_output.split(',') if p.strip())
    #构建查询条件
    def _build_query_conditions(self, filters):
        where_clauses = []
        params = []

        # 关键词搜索
        keyword = filters.get('keyword', '').strip()
        if keyword:
            where_clauses.append("sql_text LIKE %s")
            params.append(f"%{keyword}%")

        # 用户主机过滤
        user_host = filters.get('user_host', '').strip()
        if user_host:
            where_clauses.append("user_host LIKE %s")
            params.append(f"%{user_host}%")

        # 数据库名过滤
        dbname = filters.get('db', '').strip()
        if dbname:
            where_clauses.append("db = %s")
            params.append(dbname)

        # 开始时间过滤
        start_time = filters.get('start_time', '').strip()
        if start_time:
            where_clauses.append("start_time >= %s")
            params.append(start_time)

        # 结束时间过滤
        end_time = filters.get('end_time', '').strip()
        if end_time:
            where_clauses.append("start_time <= %s")
            params.append(end_time)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        return where_sql, params
    #获取总记录数
    def _get_total_count(self, cur, where_sql, params):
        count_sql = f"SELECT COUNT(*) AS cnt FROM mysql.slow_log{where_sql}"
        cur.execute(count_sql, params)
        count_row = cur.fetchone() or {}
        return int(count_row.get('cnt') or 0)
    #获取分页数据
    def _get_paged_data(self, cur, where_sql, params, page_size, offset):
        data_sql = (
            "SELECT start_time, user_host, db, query_time, lock_time, rows_sent, rows_examined, sql_text "
            "FROM mysql.slow_log"
            f"{where_sql} "
            "ORDER BY start_time DESC LIMIT %s OFFSET %s"
        )
        cur.execute(data_sql, params + [page_size, offset])
        rows = cur.fetchall() or []

        items = []
        for r in rows:
            items.append({
                'start_time': to_string(r.get('start_time')),
                'user_host': to_string(r.get('user_host')),
                'db': to_string(r.get('db')),
                'query_time': _sec(r.get('query_time')),
                'lock_time': _sec(r.get('lock_time')),
                'rows_sent': int(r.get('rows_sent') or 0),
                'rows_examined': int(r.get('rows_examined') or 0),
                'sql_text': to_string(r.get('sql_text'))
            })
        return items


slowlog_service = SlowLogService()