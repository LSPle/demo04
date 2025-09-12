import logging
from typing import List, Optional, Tuple
from ..utils.db_connection import parse_host_port

try:
    import pymysql
except ImportError:
    pymysql = None

from ..models import Instance

logger = logging.getLogger(__name__)


class DatabaseService:
    """数据库操作服务：获取实例的数据库列表等功能"""

    def __init__(self):
        self.timeout = 10  # 秒

    def list_databases(self, instance: Instance) -> Tuple[bool, List[str], str]:
        """
        获取指定实例的数据库列表
        返回: (成功标志, 数据库列表, 错误消息)
        """
        if not instance:
            return False, [], "实例不存在"
        
        # 仅支持 MySQL
        if (instance.db_type or '').strip() != 'MySQL':
            return False, [], "仅支持MySQL实例"
        
        if not pymysql:
            return False, [], "MySQL驱动不可用"
        
        conn = None
        try:
            # 建立MySQL连接
            host, port = parse_host_port(getattr(instance, 'host', ''), getattr(instance, 'port', 3306))
            conn = pymysql.connect(
                host=host,
                port=port,
                user=instance.username or '',
                password=instance.password or '',
                charset='utf8mb4',
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            with conn.cursor() as cursor:
                # 执行 SHOW DATABASES 查询
                cursor.execute("SHOW DATABASES")
                results = cursor.fetchall()
                
                # 提取数据库名称，包含系统数据库
                databases = [db_name for (db_name,) in results]
                
                return True, sorted(databases), "获取成功"
                
        except pymysql.Error as e:
            logger.error(f"MySQL连接错误 (实例ID: {instance.id}): {e}")
            return False, [], f"MySQL连接失败: {str(e)}"
        except Exception as e:
            logger.error(f"获取数据库列表异常 (实例ID: {instance.id}): {e}")
            return False, [], f"查询异常: {str(e)}"
        finally:
            # 确保连接被正确关闭
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"关闭数据库连接时出错: {e}")


# 全局实例
database_service = DatabaseService()