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
    def _tcp_probe(self, host, port):
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                return True, "MySQL端口可达"
        except Exception as e:
            return False, f"MySQL端口连接失败: {e}"

    # 验证MySQL数据库连接       
    def validate_connection(self, db_type, host, port, username=None, password=None):
       
        type_key = (db_type or '').strip()
    
        if type_key != 'MySQL':
            return False, f"不支持的数据库类型: {db_type}，本项目只支持MySQL数据库"
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
            conn.close()
            
            return True, "MySQL连接成功"
            
        except Exception as e:
            return False, f"MySQL连接失败: {e}"
    
    # 创建数据库连接
    def create_connection(self, instance, database=None):
       
        # 从实例对象中获取连接参数
        # 使用 or 操作符提供默认值，避免None值导致的错误
        host = instance.host or ''              # 主机地址，默认空字符串
        port = instance.port or 3306            # 端口号，默认3306（MySQL标准端口）
        username = instance.username or ''      # 用户名，默认空字符串
        password = instance.password or ''      # 密码，默认空字符串
        
        # 确保端口是整数类型
        # 有时候端口可能以字符串形式存储，需要转换
        if not isinstance(port, int):
            # 如果不是整数，尝试转换；如果转换失败，使用默认值3306
            port = int(port) if port else 3306
        
        # 创建并返回数据库连接
        conn = pymysql.connect(
            host=host,                      # 数据库服务器地址
            port=port,                      # 数据库服务器端口
            user=username,                  # 数据库用户名
            password=password,              # 数据库密码
            database=database,              # 要连接的数据库名称
            charset='utf8mb4',              # 字符集设置
            connect_timeout=self.timeout    # 连接超时时间
        )
        return conn
    
    # 执行mysql查询
    def execute_query(self, instance, query, database=None):
        try:
            conn = self.create_connection(instance, database)
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return True, result, ""
        except Exception as e:
            return False, None, f"查询失败: {str(e)}"


db_connection_manager = DatabaseConnectionManager()