import logging
# from typing import List, Tuple
# ThreadPoolExecutor 是Python的线程池管理器，as_completed 按“任务完成顺序”把 Future 逐个返回，而不是按提交顺序
from concurrent.futures import ThreadPoolExecutor, as_completed
# 获取当前时间戳
# from math import log
import time
import pymysql  #实现mysql连接、执行sql查询、关闭连接
from ..models import Instance
# has_app_context() 函数用于检查当前代码是否在一个 Flask 应用上下文（Application Context）中运行。
from flask import has_app_context
'''
    实例监控服务(核心)：检测单个实例，检测所有实例，更新实例状态，获取状态汇总
'''


logger = logging.getLogger(__name__)

"""实例监控服务 - 直接状态更新"""
class InstanceMonitorService:
    
    def __init__(self):
        self.max_workers = 5
        self.retry_count = 1  # 简化为1次重试，快速响应
        self.timeout = 3  # 连接超时3秒，更快响应
        # self.app 是用来 保存 Flask 应用实例，来自__init__.py 里创建的那个 app = Flask(__name__) 对象
        self.app = None

    # 注入 Flask 应用实例，用于在无上下文的线程中创建上下文，这个暂时不用管，（在__init__.py里被调用）打算删除
    def set_app(self, app):
        self.app = app

    # 新增：按信息字典检测，避免跨线程传递 ORM 实例，负责检查一个数据库实例
    def check_instance_connection_info(self, info: dict):
        """使用简单字典进行连接检测"""
        if not info:
            return False, "实例信息缺失"
        if (info.get('db_type') or '').strip() != 'MySQL':
            return True, "非MySQL实例，跳过检测"
        if not pymysql:
            return False, "MySQL驱动不可用"
        
        # 提取出参数
        host = info.get('host')
        port = int(info.get('port') or 3306)
        username = (info.get('username') or '').strip()
        password = (info.get('password') or '').strip()
        name = info.get('instance_name') or str(info.get('id'))
        
        # 重试机制
        for attempt in range(self.retry_count + 1):
            if attempt > 0:
                time.sleep(1)
            conn = None
            try:
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=username,
                    password=password,
                    connect_timeout=self.timeout,
                    read_timeout=self.timeout,
                    write_timeout=self.timeout,
                    autocommit=True
                )
                #简单测试
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                return True, "连接正常"
            except Exception as e:
                logger.warning(f"实例 {name} 第{attempt+1}次连接失败: {e}")
            finally:
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
        return False, "连接失败"
    
    # 检查所有实例，并发检测所有实例（只检测不落库，返回逐实例状态）
    def check_all_instances(self):
        """并发检测所有实例（只检测不落库，返回逐实例状态）"""
        try:
            # 查询实例列表
            if has_app_context():
                instances = Instance.query.all()
            else:
                logger.error("查询实例失败：无应用上下文")
                return 0, 0, 0, []

            if not instances:
                #return total_count, normal_count, error_count, statuses
                return 0, 0, 0, []

            total_count = len(instances)
            normal_count = 0
            error_count = 0
            statuses = []

            # 提取出数据转成普通字典，因为数据库对象不能直接在多线程里用
            inst_infos = []
            for inst in instances:
                inst_infos.append({
                    'id': inst.id,
                    'instance_name': inst.instance_name,
                    'host': inst.host,
                    'port': inst.port,
                    'username': inst.username or '',
                    'password': inst.password or '',
                    'db_type': inst.db_type,
                })

            # 并发检测（传入字典），利用多线程并发技术，快速检测所有数据库实例的连接状态（future模式！！！）
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_info = {}
                # 采用并发检测 executor.submit
                for info in inst_infos:
                    future = executor.submit(self.check_instance_connection_info, info)
                    future_to_info[future] = info

                # 采用python内置函数 as_completed 处理并发结果，作用：谁先做完就先处理谁
                for future in as_completed(future_to_info):
                    # logger.info(f"future的值: {future}")
                    info = future_to_info[future]
                    try:
                        is_connected, _msg = future.result()
                        # logger.info(f"future._state: {future._state}")
                        statuses.append({'id': int(info['id']), 'ok': bool(is_connected)})
                        if is_connected:
                            normal_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        logger.error(f"检测实例 {info.get('id')} 时出错: {e}")
                        statuses.append({'id': int(info['id']), 'ok': False})     #写死False防止意外
                        error_count += 1

            return total_count, normal_count, error_count, statuses

        except Exception as e:
            logger.error(f"并发检测所有实例失败: {e}")
            return 0, 0, 0, []


    """基于实时检测结果的汇总（不读取数据库列）"""
    def get_instance_status_summary(self):
        # _忽略其他返回值
        try:
            total, normal, error, _ = self.check_all_instances()
            return {'running': normal, 'error': error, 'total': total}
        except Exception as e:
            logger.error(f"获取实例状态汇总失败: {e}")
            return {'running': 0, 'error': 0, 'total': 0}


# 全局实例
instance_monitor_service = InstanceMonitorService()
