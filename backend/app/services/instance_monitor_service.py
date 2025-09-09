import logging
from typing import List, Tuple
from datetime import datetime

try:
    import pymysql
except ImportError:
    pymysql = None

from ..models import Instance
from .. import db

logger = logging.getLogger(__name__)


class InstanceMonitorService:
    """实例监控服务：定期检测实例连接状态并更新数据库"""

    def __init__(self):
        self.timeout = 5  # 连接超时时间（秒）

    def check_instance_connection(self, instance: Instance) -> Tuple[bool, str]:
        """
        检查单个实例的连接状态
        返回: (连接成功标志, 状态描述)
        """
        if not instance:
            return False, "实例不存在"
        
        # 目前仅支持 MySQL
        if (instance.db_type or '').strip() != 'MySQL':
            return True, "非MySQL实例，跳过检测"  # 暂时认为其他类型实例正常
        
        if not pymysql:
            return False, "MySQL驱动不可用"
        
        conn = None
        try:
            # 尝试建立MySQL连接
            conn = pymysql.connect(
                host=instance.host,
                port=instance.port,
                user=instance.username or '',
                password=instance.password or '',
                charset='utf8mb4',
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # 执行简单查询验证连接
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            return True, "连接正常"
            
        except pymysql.Error as e:
            logger.warning(f"MySQL连接错误 (ID: {instance.id}, {instance.host}:{instance.port}): {e}")
            return False, f"MySQL连接失败: {str(e)}"
        except Exception as e:
            logger.error(f"实例连接检测异常 (ID: {instance.id}, {instance.host}:{instance.port}): {e}")
            return False, f"连接检测异常: {str(e)}"
        finally:
            # 确保连接被正确关闭
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"关闭数据库连接时出错: {e}")

    def update_instance_status(self, instance: Instance, is_connected: bool, message: str = "") -> bool:
        """
        更新实例状态
        返回: 更新成功标志
        """
        try:
            if is_connected:
                # 连接正常，设置为running状态
                if instance.status != 'running':
                    instance.status = 'running'
                    logger.info(f"实例 {instance.instance_name} ({instance.id}) 状态更新为: running")
            else:
                # 连接失败，设置为error状态（表示无法连接）
                if instance.status != 'error':
                    instance.status = 'error'
                    logger.info(f"实例 {instance.instance_name} ({instance.id}) 状态更新为: error - {message}")
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"更新实例状态失败 (ID: {instance.id}): {e}")
            db.session.rollback()
            return False

    def check_all_instances(self) -> Tuple[int, int, int]:
        """
        检查所有实例的连接状态并更新数据库
        返回: (总数, 正常数, 异常数)
        """
        try:
            instances = Instance.query.all()
            total_count = len(instances)
            normal_count = 0
            error_count = 0
            
            logger.info(f"开始检测 {total_count} 个实例的连接状态")
            
            for instance in instances:
                is_connected, message = self.check_instance_connection(instance)
                self.update_instance_status(instance, is_connected, message)
                
                if is_connected:
                    normal_count += 1
                else:
                    error_count += 1
            
            logger.info(f"实例状态检测完成: 总数={total_count}, 正常={normal_count}, 异常={error_count}")
            return total_count, normal_count, error_count
            
        except Exception as e:
            logger.error(f"批量检测实例状态失败: {e}")
            return 0, 0, 0

    def get_instance_status_summary(self) -> dict:
        """
        获取实例状态汇总信息
        返回: 状态统计字典
        """
        try:
            instances = Instance.query.all()
            status_counts = {
                'running': 0,
                'warning': 0,
                'error': 0,
                'total': len(instances)
            }
            
            for instance in instances:
                status = instance.status or 'error'
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts['error'] += 1  # 未知状态归为error
            
            return status_counts
            
        except Exception as e:
            logger.error(f"获取实例状态汇总失败: {e}")
            return {'running': 0, 'warning': 0, 'error': 0, 'total': 0}


# 全局实例
instance_monitor_service = InstanceMonitorService()