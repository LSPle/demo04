import pymysql
import socket
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """数据库连接管理器"""
    
    def __init__(self):
        self.timeout = 10
    
    def _tcp_probe(self, host: str, port: int):
        """TCP端口探活"""
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                return True, "TCP端口可达"
        except Exception as e:
            return False, f"TCP连接失败: {e}"
    
    def validate_mysql(self, host: str, port: int, username: str = None, password: str = None) -> Tuple[bool, str]:
        """验证MySQL连接：若驱动不可用则退化为TCP探活"""
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=username or '',
                password=password or '',
                charset='utf8mb4',
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout
            )
            conn.ping()
            conn.close()
            return True, "MySQL连接成功"
        except Exception as e:
            return False, f"MySQL连接失败: {e}"
    
    def validate_connection(self, db_type: str, host: str, port: int, username: str = None, password: str = None) -> Tuple[bool, str]:
        """根据数据库类型验证连接：MySQL用驱动，其它类型做通用TCP探活"""
        type_key = (db_type or '').strip()
        if type_key == 'MySQL':
            return self.validate_mysql(host, port, username, password)
        # 其他类型：Redis/PostgreSQL/MongoDB/Oracle 统一TCP探活
        return self._tcp_probe(host, port)
    
    def create_connection(self, instance, database=None):
        """创建数据库连接"""
        # 获取连接参数
        host = instance.host or ''
        port = instance.port or 3306
        username = instance.username or ''
        password = instance.password or ''
        
        # 确保端口是整数
        if not isinstance(port, int):
            port = int(port) if port else 3306
        
        # 创建连接
        conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset='utf8mb4',
            connect_timeout=self.timeout
        )
        return conn
    
    def test_connection(self, instance):
        """测试数据库连接"""
        try:
            conn = self.create_connection(instance)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True, "连接成功"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def execute_query(self, instance, query, database=None):
        """执行查询"""
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

# 创建全局实例
db_connection_manager = DatabaseConnectionManager()