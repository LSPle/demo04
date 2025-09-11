import logging
from typing import Optional, Tuple, Any, Dict
from contextlib import contextmanager

try:
    import pymysql
except ImportError:
    pymysql = None

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """数据库连接管理器：统一处理MySQL连接和错误处理"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def _create_connection_params(self, instance, database: Optional[str] = None) -> Dict[str, Any]:
        """创建连接参数字典"""
        params = {
            'host': instance.host,
            'port': instance.port,
            'user': instance.username or '',
            'password': instance.password or '',
            'charset': 'utf8mb4',
            'connect_timeout': self.timeout,
            'read_timeout': self.timeout,
            'write_timeout': self.timeout
        }
        
        if database:
            params['database'] = database
            
        return params
    
    @contextmanager
    def get_connection(self, instance, database: Optional[str] = None, cursor_class=None):
        """获取数据库连接的上下文管理器"""
        if not pymysql:
            raise RuntimeError("MySQL驱动不可用")
        
        conn = None
        try:
            params = self._create_connection_params(instance, database)
            if cursor_class:
                params['cursorclass'] = cursor_class
            
            conn = pymysql.connect(**params)
            yield conn
            
        except pymysql.Error as e:
            logger.warning(f"MySQL连接错误 (实例ID: {getattr(instance, 'id', 'unknown')}, {instance.host}:{instance.port}): {e}")
            raise
        except Exception as e:
            logger.error(f"数据库连接异常 (实例ID: {getattr(instance, 'id', 'unknown')}, {instance.host}:{instance.port}): {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"关闭数据库连接时出错: {e}")
    
    def test_connection(self, instance) -> Tuple[bool, str]:
        """测试数据库连接"""
        if not pymysql:
            return False, "MySQL驱动不可用"
        
        try:
            with self.get_connection(instance) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            return True, "连接正常"
            
        except pymysql.Error as e:
            return False, f"MySQL连接失败: {str(e)}"
        except Exception as e:
            return False, f"连接检测异常: {str(e)}"
    
    def execute_query(self, instance, query: str, database: Optional[str] = None, 
                     cursor_class=None, fetch_all: bool = True) -> Tuple[bool, Any, str]:
        """执行查询并返回结果"""
        try:
            with self.get_connection(instance, database, cursor_class) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    if fetch_all:
                        result = cursor.fetchall()
                    else:
                        result = cursor.fetchone()
                    return True, result, ""
                    
        except Exception as e:
            error_msg = f"查询执行失败: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg


# 全局实例
db_connection_manager = DatabaseConnectionManager()