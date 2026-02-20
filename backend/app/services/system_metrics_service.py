import psutil
import time
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

"""    
    轻量级系统指标采集服务，使用psutil替代Prometheus(保留)
    获取CPU使用率、内存使用率、磁盘使用率、磁盘I/O、网络I/O
"""
class SystemMetricsService:

    #初始化   
    def __init__(self):
        self.cache_duration = 5                                      # 缓存5秒，避免频繁采集
        self._cache = {}                                             # 系统指标缓存字典，存储各种性能数据
        self._last_update = 0                                        # 上次缓存更新的时间戳，用于判断是否需要刷新缓存
        # 上一次磁盘IO快照（用于估算I/O延迟）
        self._last_disk_io: Optional[psutil._common.sdiskio] = None  # 存储上次磁盘IO统计数据
        self._last_disk_ts: float = 0.0                              # 上次磁盘IO采样的时间戳
   
    # 判断是否需要更新缓存
    def should_update_cache(self):
        return time.time() - self._last_update > self.cache_duration

    # 更新系统指标缓存
    def update_cache(self):
        try:
            # CPU使用率（1秒采样）
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用情况（根目录）
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 磁盘I/O统计（含读写次数/字节/耗时）
            disk_io = psutil.disk_io_counters()
            now_ts = time.time()

            # 估算平均I/O延迟（毫秒/操作）：Δ(read_time+write_time) / Δ(read_count+write_count)
            io_latency_ms = None
            try:
                if disk_io is not None and hasattr(disk_io, 'read_time') and hasattr(disk_io, 'write_time'):
                    if self._last_disk_io is not None:
                        read_time_diff = max(0, (getattr(disk_io, 'read_time', 0) or 0) - (getattr(self._last_disk_io, 'read_time', 0) or 0))
                        write_time_diff = max(0, (getattr(disk_io, 'write_time', 0) or 0) - (getattr(self._last_disk_io, 'write_time', 0) or 0))
                        op_count_diff = max(0, (getattr(disk_io, 'read_count', 0) or 0) - (getattr(self._last_disk_io, 'read_count', 0) or 0)) 
                        op_count_diff += max(0, (getattr(disk_io, 'write_count', 0) or 0) - (getattr(self._last_disk_io, 'write_count', 0) or 0))

                        if op_count_diff > 0:
                            # psutil 的 read_time/write_time 通常是毫秒
                            io_latency_ms = round((read_time_diff + write_time_diff) / op_count_diff, 2)
                    # 更新快照
                    self._last_disk_io = disk_io
                    self._last_disk_ts = now_ts
            except Exception:
                io_latency_ms = None
            
            # 网络I/O统计
            net_io = psutil.net_io_counters()
            
            # 构建系统指标缓存数据结构
            self._cache = {
                'cpu_usage': round(cpu_percent, 2),                     # CPU使用率，保留2位小数
                'memory_usage': round(memory_percent, 2),               # 内存使用率，保留2位小数
                # 磁盘使用情况
                'disk_usage': {
                    'used_gb': round(disk.used / (1024**3), 1),        # 已使用空间（GB），保留1位小数
                    'total_gb': round(disk.total / (1024**3), 1),      # 总空间（GB），保留1位小数
                    'usage_percent': round(disk_percent, 2),           # 磁盘使用率百分比，保留2位小数
                    'storage_display': f'{round(disk.used / (1024**3), 1)}GB / {round(disk.total / (1024**3), 1)}GB'  # 存储显示格式
                },
                # 磁盘I/O统计
                'disk_io': {
                    'read_bytes': disk_io.read_bytes if disk_io else 0,    # 读取字节数
                    'write_bytes': disk_io.write_bytes if disk_io else 0,  # 写入字节数
                    'read_count': disk_io.read_count if disk_io else 0,    # 读取次数
                    'write_count': disk_io.write_count if disk_io else 0,  # 写入次数
                    'io_latency_ms': io_latency_ms                         # I/O延迟（毫秒）
                },
                # 网络I/O统计
                'network_io': {
                    'bytes_sent': net_io.bytes_sent if net_io else 0,      # 发送字节数
                    'bytes_recv': net_io.bytes_recv if net_io else 0,      # 接收字节数
                    'packets_sent': net_io.packets_sent if net_io else 0,  # 发送数据包数
                    'packets_recv': net_io.packets_recv if net_io else 0   # 接收数据包数
                },
                
                'timestamp': int(time.time())                              # 数据采集时间戳
            }
            self._last_update = time.time()
            
        except Exception as e:
            logger.error(f"系统指标采集失败: {e}")
            # 保持旧缓存或返回空值
            if not self._cache:
                self._cache = {
                    'cpu_usage': None,
                    'memory_usage': None,
                    'disk_usage': None,
                    'disk_io': None,
                    'network_io': None,
                    'io_latency_ms': None,
                    'timestamp': int(time.time())
                }
    # 获取CPU使用率百分比
    def get_cpu_usage(self):
        if self.should_update_cache():
            self.update_cache()
        return self._cache.get('cpu_usage')
    # 获取内存使用率百分比
    def get_memory_usage(self):
        if self.should_update_cache():
            self.update_cache()
        return self._cache.get('memory_usage')
    # 获取磁盘使用情况
    def get_disk_usage(self):
        if self.should_update_cache():
            self.update_cache()
        return self._cache.get('disk_usage')
    # 获取磁盘I/O统计
    def get_disk_io_stats(self):
        if self.should_update_cache():
            self.update_cache()
        return self._cache.get('disk_io')
    # 获取估算的平均磁盘I/O延迟（毫秒/操作）
    def get_io_latency_ms(self):
        if self.should_update_cache():
            self.update_cache()
        dio = None
        dio = self._cache.get('disk_io') or {}
        return dio.get('io_latency_ms')
    # 获取网络I/O统计
    def get_network_io_stats(self):
        if self.should_update_cache():
            self.update_cache()
        return self._cache.get('network_io')
    # 获取所有系统指标
    def get_all_metrics(self):
        if self.should_update_cache():
            self.update_cache()
        
        return {
            'service': 'system',                                                       # 服务标识，标记这是系统指标数据
            'cpu_usage': self._cache.get('cpu_usage'),                                 # CPU使用率百分比（0-100）
            'memory_usage': self._cache.get('memory_usage'),                           # 内存使用情况（已用/总量/百分比）
            'disk_usage': self._cache.get('disk_usage'),                               # 磁盘使用情况（已用/总量/百分比/显示格式）
            'disk_io': self._cache.get('disk_io'),                                     # 磁盘I/O统计（读写字节数/次数/延迟）
            'network_io': self._cache.get('network_io'),                               # 网络I/O统计（发送/接收字节数/包数）
            'io_latency_ms': (self._cache.get('disk_io') or {}).get('io_latency_ms'),  # 磁盘I/O延迟毫秒数（单独提取便于监控）
            'timestamp': self._cache.get('timestamp')                                  # 数据采集时间戳，用于判断数据新鲜度
        }
    # 获取系统基本信息
    # def get_system_info(self):
    #     try:
    #         return {
    #             'platform': psutil.WINDOWS if psutil.WINDOWS else 'unix',                # 操作系统平台类型
    #             'cpu_count': psutil.cpu_count(),                                         # 物理CPU核心数
    #             'cpu_count_logical': psutil.cpu_count(logical=True),                     # 逻辑CPU核心数
    #             'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 1),  # 系统总内存大小（GB，保留1位小数）
    #             'boot_time': psutil.boot_time(),                                         # 系统启动时间戳
    #             'python_version': psutil.version_info                                    # psutil库版本信息
    #         }
    #     except Exception as e:
    #         logger.error(f"获取系统信息失败: {e}")
    #         return {}
    
    def health_check(self):
        """健康检查"""
        try:
            # 简单测试psutil功能
            psutil.cpu_percent()
            return True
        except Exception:
            return False


# 全局实例
system_metrics_service = SystemMetricsService()