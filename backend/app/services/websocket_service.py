# 顶部导入与类定义片段（class WebSocketService）
import logging
from flask_socketio import SocketIO, emit
from threading import Thread, Lock
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WebSocketService:
    """WebSocket服务：处理实时状态更新推送"""
    
    def __init__(self, socketio: SocketIO = None, app=None):
        self.socketio = socketio
        self.app = app
        self.monitoring_thread = None
        self.monitoring_active = False
        self.last_status = {}
        # 新增：会话计数与锁
        self._session_lock = Lock()
        self._active_sessions = 0
        # 动态检测频率配置
        self.base_interval = 5  # 基础检测间隔（秒）
        self.min_interval = 3   # 最小检测间隔（秒）
        self.max_interval = 15  # 最大检测间隔（秒）
        
    def init_socketio(self, socketio: SocketIO, app=None):
        """初始化SocketIO实例"""
        self.socketio = socketio
        if app:
            self.app = app
        
    def start_monitoring(self):
        """启动实时监控线程"""
        try:
            if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
                if not self.app:
                    logger.error("无法启动监控线程：app实例未设置")
                    return
                    
                self.monitoring_active = True
                self.monitoring_thread = Thread(target=self._monitor_instances)
                self.monitoring_thread.daemon = True
                self.monitoring_thread.start()
                logger.info("实时监控线程已启动")
            else:
                logger.info("监控线程已在运行")
        except Exception as e:
            logger.error(f"启动监控线程失败: {e}")
            
    def stop_monitoring(self):
        """停止实时监控线程"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("实时监控线程已停止")
        
    # 新增：登录后调用，首个会话触发启动
    def increment_active_sessions(self) -> int:
        with self._session_lock:
            self._active_sessions += 1
            count = self._active_sessions
        if count == 1:
            self.start_monitoring()
        logger.info(f"活跃会话数增加：{count}")
        return count

    # 新增：退出登录后调用，最后一个会话触发停止
    def decrement_active_sessions(self) -> int:
        with self._session_lock:
            self._active_sessions = max(0, self._active_sessions - 1)
            count = self._active_sessions
        if count == 0:
            self.stop_monitoring()
        logger.info(f"活跃会话数减少：{count}")
        return count

    def _monitor_instances(self):
        """监控实例状态变化的后台线程 - 优化版本使用并发检测"""
        from ..services.instance_monitor_service import instance_monitor_service
        from ..models import Instance
        from .. import db
        
        while self.monitoring_active:
            try:
                # 在应用上下文中执行
                with self.app.app_context():
                    start_time = time.time()
                    
                    # 使用优化后的并发检测方法
                    total_count, normal_count, error_count = instance_monitor_service.check_all_instances()
                    
                    if total_count > 0:
                        # 获取更新后的实例状态
                        instances = Instance.query.all()
                        current_status = {}
                        status_changed = False
                        
                        for instance in instances:
                            new_status = instance.status or 'error'
                            
                            current_status[instance.id] = {
                                'id': instance.id,
                                'name': instance.instance_name,
                                'host': instance.host,
                                'port': instance.port,
                                'status': new_status,
                                'message': '连接正常' if new_status == 'running' else '连接异常',
                                'timestamp': time.time()
                            }
                            
                            # 检查状态是否发生变化
                            if (instance.id not in self.last_status or 
                                self.last_status[instance.id]['status'] != new_status):
                                status_changed = True
                                logger.info(f"实例 {instance.instance_name} 状态变化: {self.last_status.get(instance.id, {}).get('status', 'unknown')} -> {new_status}")
                        
                        # 如果有状态变化，广播更新
                        if status_changed:
                            # 发送实例状态更新
                            self.socketio.emit('instances_status_update', {
                                'instances': list(current_status.values()),
                                'summary': self._calculate_summary(current_status)
                            })
                            
                            # 发送状态汇总更新
                            summary = self._calculate_summary(current_status)
                            logger.info(f"发送状态汇总更新: 总数{summary['total']}, 运行{summary['running']}, 错误{summary['error']}")
                        
                        self.last_status = current_status
                        
                        elapsed_time = time.time() - start_time
                        logger.debug(f"监控周期完成: 检测{total_count}个实例, 正常{normal_count}, 异常{error_count}, 耗时{elapsed_time:.2f}秒")
                
            except Exception as e:
                logger.error(f"监控线程执行出错: {e}")
                
            # 动态调整检测间隔
            sleep_interval = self._calculate_sleep_interval(total_count, elapsed_time if 'elapsed_time' in locals() else 0)
            time.sleep(sleep_interval)
            
    # 已删除未使用的状态变更通知方法
    # def _emit_instance_status_change(self, instance_data: Dict[str, Any]):
    # def _emit_status_summary(self, summary: Dict[str, Any]):
            
    def _calculate_summary(self, current_status: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """计算状态汇总信息"""
        total = len(current_status)
        running = sum(1 for status in current_status.values() if status['status'] == 'running')
        error = sum(1 for status in current_status.values() if status['status'] == 'error')
        
        return {
            'total': total,
            'running': running,
            'error': error,
            'warning': 0,  # 暂时没有warning状态的逻辑
            'timestamp': time.time()
        }
        
    def _calculate_sleep_interval(self, instance_count: int, elapsed_time: float) -> float:
        """根据实例数量和检测耗时动态计算检测间隔"""
        # 基于实例数量调整：实例越多，间隔越长
        if instance_count <= 5:
            base = self.min_interval
        elif instance_count <= 20:
            base = self.base_interval
        else:
            base = self.max_interval
        
        # 基于检测耗时调整：检测时间越长，间隔越长
        if elapsed_time > 2:
            base = min(base * 1.5, self.max_interval)
        elif elapsed_time > 5:
            base = self.max_interval
        
        return max(self.min_interval, min(base, self.max_interval))
        
    def broadcast_current_status(self):
        """广播当前所有实例状态"""
        if self.socketio and self.last_status:
            instances_list = list(self.last_status.values())
            summary = self._calculate_summary(self.last_status)
            
            self.socketio.emit('instances_status_update', {
                'instances': instances_list,
                'summary': summary
            })

# 全局实例
websocket_service = WebSocketService()