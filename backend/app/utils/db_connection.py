# 导入需要的模块
import pymysql  # MySQL数据库连接驱动
import socket   # 网络连接模块，用于TCP端口检测
import logging  # 日志记录模块

# 创建日志记录器
logger = logging.getLogger(__name__)


"""
    数据库连接管理器
    
    这个类用来管理和验证数据库连接，主要功能包括：
    1. 验证MySQL数据库连接是否正常
    2. 检测TCP端口是否可达
    3. 创建数据库连接
    4. 执行数据库查询
"""
# 数据库连接管理器
class DatabaseConnectionManager:

    # 初始化
    def __init__(self):
        self.timeout = 10
    
    # MySQL端口连通性检查：在进行完整的MySQL连接验证之前，可以先用这个方法快速检查网络连通性
    # def _tcp_probe(self, host, port):
    #     try:
    #         with socket.create_connection((host, port), timeout=self.timeout):
    #             return True, "MySQL端口可达"
    #     except Exception as e:
    #         return False, f"MySQL端口连接失败: {e}"

    # 验证MySQL数据库连接       
    def validate_connection(self, db_type, host, port, username=None, password=None):
       
        type_key = (db_type or '').strip()
    
        if type_key != 'MySQL':
            return False, f"不支持的数据库类型: {db_type}，本项目只支持MySQL数据库"
        conn = None
        try:
            conn = pymysql.connect(
                host=host,                          # 数据库服务器地址
                port=port,                          # 数据库服务器端口
                user=username or '',                # 用户名，如果为None则使用空字符串
                password=password or '',            # 密码，如果为None则使用空字符串
                charset='utf8mb4',                  # 字符集
                connect_timeout=self.timeout,       # 连接超时时间
                read_timeout=self.timeout,          # 读取超时时间
                write_timeout=self.timeout          # 写入超时时间
            )
            conn.ping()
            return True, "MySQL连接成功"
            
        except Exception as e:
            return False, f"MySQL连接失败: {e}"
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    
    # 创建数据库连接
    def create_connection(self, instance, database=None, cursorclass=None, read_timeout=None, write_timeout=None, connect_timeout=None):
        host = instance.host or ''
        port = instance.port
        username = instance.username or ''
        password = instance.password or ''

        try:
            port = int(port) if port else 3306
        except Exception:
            port = 3306

        conn_kwargs = {
            'host': host,
            'port': port,
            'user': username,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'connect_timeout': connect_timeout or self.timeout,
            'read_timeout': read_timeout or self.timeout,
            'write_timeout': write_timeout or self.timeout
        }
        if cursorclass is not None:
            conn_kwargs['cursorclass'] = cursorclass
        return pymysql.connect(**conn_kwargs)
    
    # 执行mysql查询
    def execute_query(self, instance, query, database=None, cursorclass=None):
        conn = None
        cursor = None
        try:
            conn = self.create_connection(instance, database, cursorclass=cursorclass)
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            return True, result, ""
        except Exception as e:
            return False, None, f"查询失败: {str(e)}"
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass


db_connection_manager = DatabaseConnectionManager()
