import logging
import datetime
from typing import Any, Dict, List, Tuple, Optional
import pymysql
from ..models import Instance
from ..utils.db_connection import db_connection_manager

# try:
#     import pymysql
# except ImportError:
#     pymysql = None

'''
  慢查询日志分析服务
'''
logger = logging.getLogger(__name__)


# 将时间值转换为秒数
def second(val):
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

# 将各种类型的值转换为字符串，用于JSON序列化
def to_string(val):
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
class slowLogService: 
    #初始化慢查询服务
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    #连接MySQL实例
    def mysql_connect(self, inst: Instance):
        return db_connection_manager.create_connection(
            instance=inst,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            write_timeout=self.timeout
        )

    #分析MySQL慢查询日志
    def analyze(self, inst: Instance, top: int = 20, min_avg_ms: int = 10):

        # 基本参数检查
        if not inst:
            return False, {}, "实例不存在"
        if (inst.db_type or '').strip() != 'MySQL':
            return False, {}, "仅支持MySQL实例"

        conn = None
        try:
            conn = self.mysql_connect(inst)
            if not conn:
                return False, {}, "MySQL连接失败"

            # 慢查询整体配置与状态信息
            overview = {}
            # performance_schema 的 Top SQL 统计结果
            ps_top = []
            # 过程中的提示信息（如未开启相关功能）
            warnings = []

            with conn.cursor() as cur:
                overview = self._get_mysql_config(cur)

                if overview.get('performance_schema'):
                    ps_top = self._get_top_sql_from_ps(cur, top, min_avg_ms)
                else:
                    warnings.append('performance_schema 未开启，无法生成 Top SQL 指纹统计')

            data = {
                'overview': overview,
                'ps_top': ps_top,
                'warnings': warnings
            }
            return True, data, 'OK'
                
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
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    #获取MySQL慢查询相关配置
    def _get_mysql_config(self, cur):
       
        cur.execute("""
            SHOW GLOBAL VARIABLES WHERE Variable_name IN (
              'performance_schema', 'long_query_time', 'slow_query_log', 'log_output', 'slow_query_log_file'
            )
        """)
        # 获取查询结果，如果为空则使用空列表
        rows = cur.fetchall()
        vars_dict = {}
        for row in rows:
            variable_name = row['Variable_name']
            variable_value = row['Value']
            vars_dict[variable_name] = variable_value

        # 统一慢查询日志格式
        # 检查performance_schema是否开启
        if vars_dict.get('performance_schema', '').upper() == 'ON':
            performance_schema_on = True
        else:
            performance_schema_on = False

        # 检查慢查询日志是否开启
        if vars_dict.get('slow_query_log', '').upper() == 'ON':
            slow_query_log = True
        else:
            slow_query_log = False

        # 获取慢查询时间阈值
        long_query_time = vars_dict.get('long_query_time')
        # 获取日志输出方式
        log_output_raw = str(vars_dict.get('log_output') or '')
        # 获取慢查询日志文件路径
        slow_file = str(vars_dict.get('slow_query_log_file') or '').strip()

        return {
            'performance_schema': performance_schema_on,
            'slow_query_log': slow_query_log,
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
            rows = cur.fetchall()
        except Exception:
            return []
      
        top_list = []      # 存储慢查询统计结果的列表
        for r in rows:
            # 获取SQL执行次数
            cnt = int(r.get('count_star') or 0)
            # 计算平均执行时间和总执行时间
            avg_ms, total_ms = self.get_time_info(r.get('sum_timer_wait'), cnt)           
            # 获取扫描和返回的行数统计
            rows_examined = int(r.get('sum_rows_examined') or 0)
            rows_sent = int(r.get('sum_rows_sent') or 0)
            # 计算平均扫描行数
            if cnt:
                rows_examined_avg = rows_examined / cnt
            else:
                rows_examined_avg = 0.0
            
            # 计算平均返回行数
            if cnt:
                rows_sent_avg = rows_sent / cnt
            else:
                rows_sent_avg = 0.0
            
            # 构建慢查询统计结果字典
            top_list.append({
                'schema': r.get('schema_name') or '',              # 数据库名
                'digest': r.get('digest') or '',                   # SQL摘要ID
                'query': (r.get('digest_text') or '')[:500],       # SQL语句（截取前500字符）
                'count': cnt,                                      # 执行次数
                'avg_latency_ms': round(avg_ms, 2),                # 平均执行时间（毫秒）
                'total_latency_ms': round(total_ms, 2),            # 总执行时间（毫秒）
                'rows_examined_avg': round(rows_examined_avg, 1),  # 平均扫描行数
                'rows_sent_avg': round(rows_sent_avg, 1),          # 平均返回行数
            })
        return top_list
    #计算平均和总执行时间
    def get_time_info(self, timer_ps, cnt: int):
        try:
            ps = int(timer_ps)
            total_ms = ps / 1000000000.0  # 转换为毫秒
        except Exception:
            return 0.0, 0.0
        
        # 计算平均执行时间，避免除零错误
        if cnt:
            avg_ms = total_ms / cnt
        else:
            avg_ms = 0.0
        return avg_ms, total_ms
    # 从mysql.slow_log表分页查询慢查询记录
    def list_from_table(
        self,
        inst: Instance,
        page: int = 1,
        page_size: int = 10,
        filters=None):
        # 基本参数检查
        if not inst:
            return False, {}, "实例不存在"
        if (inst.db_type or '').strip() != 'MySQL':
            return False, {}, "仅支持MySQL实例"

        conn = None
        try:
            conn = self.mysql_connect(inst)
            if not conn:
                return False, {}, "MySQL连接失败"

            with conn.cursor() as cur:
                overview = self.check_slow_log_config(cur)
                log_output = str(overview.get('log_output') or '').upper()
                if not self.is_table_output_enabled(overview):
                    if 'FILE' in log_output:
                        return False, {'overview': overview}, "慢查询日志为FILE输出，仅支持TABLE方式"
                    return False, {'overview': overview}, "仅支持 log_output 包含 TABLE 的数据库"

                where_sql, params = self.query_conditions(filters)

                total = self.get_total_count(cur, where_sql, params)

                if str(page).isdigit():
                    page = max(1, int(page))
                else:
                    page = 1

                if str(page_size).isdigit():
                    page_size = int(page_size)
                    if page_size < 1:
                        page_size = 1
                    elif page_size > 100:
                        page_size = 100
                else:
                    page_size = 10
                offset = (page - 1) * page_size

                items = self.get_paged_data(cur, where_sql, params, page_size, offset)

                data = {
                    'overview': overview,
                    'items': items,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }
                return True, data, 'OK'
                
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
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    #检查慢查询日志配置
    def check_slow_log_config(self, cur):
        
        cur.execute(
            "SHOW GLOBAL VARIABLES WHERE Variable_name IN ('slow_query_log','log_output')"
        )
        rows = cur.fetchall()
        # 将查询结果转换为字典格式，方便后续使用
        vars_dict = {}
        for r in rows:
            vars_dict[r['Variable_name']] = r['Value']

        return {
            'slow_query_log': str(vars_dict.get('slow_query_log') or ''),
            'log_output': str(vars_dict.get('log_output') or ''),
        }
    #检查是否启用了TABLE输出
    def is_table_output_enabled(self, overview):
        # 获取MySQL的log_output配置值
        log_output = overview.get('log_output')
        
        # 如果配置为空，返回False
        if not log_output:
            return False
            
        # 转换为大写字符串，便于比较
        log_output = str(log_output).strip().upper()
        
        # 检查是否包含TABLE输出
        # 支持的配置: 'TABLE' 或 'TABLE,FILE'
        # 不支持的配置: 'FILE' 或 'NONE'
        if 'TABLE' in log_output:
            return True
        else:
            return False
    #构建查询条件
    def query_conditions(self, filters):
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
    def get_total_count(self, cur, where_sql, params):
        count_sql = f"SELECT COUNT(*) AS cnt FROM mysql.slow_log{where_sql}"
        cur.execute(count_sql, params)
        count_row = cur.fetchone() or {}
        return int(count_row.get('cnt') or 0)
    #获取分页数据
    def get_paged_data(self, cur, where_sql, params, page_size, offset):
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
            # 将数据库查询结果转换为前端需要的格式
            items.append({
                'start_time': to_string(r.get('start_time')),        # 查询开始时间，转换为字符串
                'user_host': to_string(r.get('user_host')),          # 用户和主机信息，转换为字符串
                'db': to_string(r.get('db')),                        # 数据库名称，转换为字符串
                'query_time': second(r.get('query_time')),             # 查询执行时间，转换为秒数
                'lock_time': second(r.get('lock_time')),               # 锁等待时间，转换为秒数
                'rows_sent': int(r.get('rows_sent') or 0),           # 返回的行数，转换为整数，默认0
                'rows_examined': int(r.get('rows_examined') or 0),   # 检查的行数，转换为整数，默认0
                'sql_text': to_string(r.get('sql_text'))             # SQL语句文本，转换为字符串
            })
        return items


slowlog_service = slowLogService()
