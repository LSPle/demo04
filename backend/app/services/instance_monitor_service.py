import logging
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pymysql  #实现mysql连接、执行sql查询、关闭连接
from ..models import Instance
from .. import db
'''
    实例监控服务(核心)：检测单个实例，检测所有实例，更新实例状态，获取状态汇总
'''


logger = logging.getLogger(__name__)


class InstanceMonitorService:
    """简化版实例监控服务"""

    def __init__(self):
        self.timeout = 15 # 超时时间10秒
        self.max_workers = 15  # 并发检测线程数
        self.retry_count = 3  # 重试2次
        self.failure_counts = {}  # 失败计数器
        self.failure_threshold = 3  # 连续失败3次才标记异常
        self.success_threshold = 2  # 新增：成功阈值2次

    def check_instance_connection(self, instance):
        """检查实例连接状态"""
        if not instance:
            return False, "实例不存在"
        
        # 仅支持MySQL
        if (instance.db_type or '').strip() != 'MySQL':
            return True, "非MySQL实例，跳过检测"
        
        if not pymysql:
            return False, "MySQL驱动不可用"
        
        # 重试机制
        for attempt in range(self.retry_count + 1):
            if attempt > 0:
                time.sleep(1)  # 重试间隔1秒
            
            try:
                # 建立连接
                conn = pymysql.connect(
                    host=instance.host,
                    port=instance.port,
                    user=instance.username or '',
                    password=instance.password or '',
                    connect_timeout=self.timeout,
                    autocommit=True
                )
                
                #测试查询
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                conn.close()
                
              

                
                # 连接成功，重置失败计数
                if instance.id in self.failure_counts:
                    del self.failure_counts[instance.id]
                
                return True, "连接正常"
                
            except Exception as e:
                if attempt == self.retry_count:  # 最后一次重试
                    return False, f"连接失败: {str(e)}"
        
        return False, "连接失败"

    #不太明白
    def update_instance_status(self, instance: Instance, is_connected: bool, message: str = ""):
        """更新实例状态 - 状态平滑机制"""
        try:
            if is_connected:
                # 连接正常
                if instance.id in self.failure_counts:
                    del self.failure_counts[instance.id]
                
                if instance.status != 'running':
                    instance.status = 'running'
                    logger.info(f"实例 {instance.instance_name} 状态更新为: running")
            else:
                # 连接失败，累计失败次数
                if instance.id not in self.failure_counts:
                    self.failure_counts[instance.id] = 0
                
                self.failure_counts[instance.id] += 1
                
                # 连续失败2次才标记为error
                if self.failure_counts[instance.id] >= self.failure_threshold:
                    if instance.status != 'error':
                        instance.status = 'error'
                        logger.info(f"实例 {instance.instance_name} 连续失败{self.failure_counts[instance.id]}次，状态更新为: error")
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"更新实例状态失败: {e}")
            db.session.rollback()
            return False

    def check_all_instances(self):
        """并发检测所有实例"""
        try:
            instances = Instance.query.all()
            if not instances:
                return 0, 0, 0
            
            total_count = len(instances)
            normal_count = 0
            error_count = 0
            
            # 并发检测
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_instance = {
                    executor.submit(self.check_instance_connection, instance): instance
                    for instance in instances
                }
                
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
            
            logger.info(f"实例检测完成: 总数={total_count}, 正常={normal_count}, 异常={error_count}")
            return total_count, normal_count, error_count
            
        except Exception as e:
            logger.error(f"批量检测实例状态失败: {e}")
            return 0, 0, 0

    def get_instance_status_summary(self):
        """获取实例状态汇总"""
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
                    status_counts['error'] += 1
            
            return status_counts
            
        except Exception as e:
            logger.error(f"获取实例状态汇总失败: {e}")
            return {'running': 0, 'warning': 0, 'error': 0, 'total': 0}


# 全局实例
instance_monitor_service = InstanceMonitorService()