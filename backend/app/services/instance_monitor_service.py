import logging
from typing import List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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
        self.timeout = 3  # 连接超时时间（秒）- 从5秒优化到3秒
        self.max_workers = 10  # 并发检测线程数

    def check_instance_connection(self, instance: Instance, app_context=None) -> Tuple[bool, str]:
        """
        检查单个实例的连接状态
        参数: 
            instance - 实例对象
            app_context - Flask应用上下文（用于线程池中的数据库操作）
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
            # 尝试建立MySQL连接 - 优化连接参数
            conn = pymysql.connect(
                host=instance.host,
                port=instance.port,
                user=instance.username or '',
                password=instance.password or '',
                charset='utf8mb4',
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout,
                autocommit=True,  # 自动提交，减少事务开销
                cursorclass=pymysql.cursors.Cursor  # 使用默认游标类型
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

    def check_all_instances(self, user_id: str = None) -> Tuple[int, int, int]:
        """
        检查实例的连接状态并更新数据库 - 使用并发检测优化性能
        参数: user_id - 用户ID，如果提供则只检查该用户的实例，否则检查所有实例
        返回: (总数, 正常数, 异常数)
        """
        from flask import current_app
        
        try:
            if user_id:
                instances = Instance.query.filter_by(user_id=user_id).all()
            else:
                instances = Instance.query.all()
            total_count = len(instances)
            normal_count = 0
            error_count = 0
            
            if total_count == 0:
                return 0, 0, 0
            
            logger.info(f"开始并发检测 {total_count} 个实例的连接状态")
            start_time = time.time()
            
            # 使用线程池并发检测实例连接状态
            with ThreadPoolExecutor(max_workers=min(self.max_workers, total_count)) as executor:
                # 提交所有检测任务，传递应用上下文
                future_to_instance = {
                    executor.submit(self._check_instance_with_context, instance, current_app._get_current_object()): instance 
                    for instance in instances
                }
                
                # 收集检测结果并更新状态
                for future in as_completed(future_to_instance):
                    instance = future_to_instance[future]
                    try:
                        is_connected, message = future.result()
                        self.update_instance_status(instance, is_connected, message)
                        
                        if is_connected:
                            normal_count += 1
                        else:
                            error_count += 1
                            
                    except Exception as e:
                        logger.error(f"检测实例 {instance.id} 时出错: {e}")
                        self.update_instance_status(instance, False, f"检测异常: {str(e)}")
                        error_count += 1
            
            elapsed_time = time.time() - start_time
            logger.info(f"实例状态检测完成: 总数={total_count}, 正常={normal_count}, 异常={error_count}, 耗时={elapsed_time:.2f}秒")
            return total_count, normal_count, error_count
            
        except Exception as e:
            logger.error(f"批量检测实例状态失败: {e}")
            return 0, 0, 0

    def _check_instance_with_context(self, instance: Instance, app) -> Tuple[bool, str]:
        """
        在应用上下文中检查实例连接状态
        """
        with app.app_context():
            return self.check_instance_connection(instance)

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