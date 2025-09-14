import psutil
import time
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class SystemMetricsService:
    """轻量级系统指标采集服务，使用psutil替代Prometheus
    
    优势：
    - 无需外部依赖（Prometheus服务器）
    - 部署简单，开箱即用
    - 资源占用低
    - 跨平台兼容
    """
    
    def __init__(self):
        self.cache_duration = 5  # 缓存5秒，避免频繁采集
        self._cache = {}
        self._last_update = 0
    
    def _should_update_cache(self) -> bool:
        """判断是否需要更新缓存"""
        return time.time() - self._last_update > self.cache_duration
    
    def _update_cache(self):
        """更新系统指标缓存"""
        try:
            # CPU使用率（1秒采样）
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用情况（根目录）
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 磁盘I/O统计
            disk_io = psutil.disk_io_counters()
            
            # 网络I/O统计
            net_io = psutil.net_io_counters()
            
            self._cache = {
                'cpu_usage': round(cpu_percent, 2),
                'memory_usage': round(memory_percent, 2),
                'disk_usage': {
                    'used_gb': round(disk.used / (1024**3), 1),
                    'total_gb': round(disk.total / (1024**3), 1),
                    'usage_percent': round(disk_percent, 2),
                    'storage_display': f'{round(disk.used / (1024**3), 1)}GB / {round(disk.total / (1024**3), 1)}GB'
                },
                'disk_io': {
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0,
                    'read_count': disk_io.read_count if disk_io else 0,
                    'write_count': disk_io.write_count if disk_io else 0
                },
                'network_io': {
                    'bytes_sent': net_io.bytes_sent if net_io else 0,
                    'bytes_recv': net_io.bytes_recv if net_io else 0,
                    'packets_sent': net_io.packets_sent if net_io else 0,
                    'packets_recv': net_io.packets_recv if net_io else 0
                },
                'timestamp': int(time.time())
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
                    'timestamp': int(time.time())
                }
    
    def get_cpu_usage(self) -> Optional[float]:
        """获取CPU使用率百分比"""
        if self._should_update_cache():
            self._update_cache()
        return self._cache.get('cpu_usage')
    
    def get_memory_usage(self) -> Optional[float]:
        """获取内存使用率百分比"""
        if self._should_update_cache():
            self._update_cache()
        return self._cache.get('memory_usage')
    
    def get_disk_usage(self) -> Optional[Dict[str, Any]]:
        """获取磁盘使用情况"""
        if self._should_update_cache():
            self._update_cache()
        return self._cache.get('disk_usage')
    
    def get_disk_io_stats(self) -> Optional[Dict[str, Any]]:
        """获取磁盘I/O统计"""
        if self._should_update_cache():
            self._update_cache()
        return self._cache.get('disk_io')
    
    def get_network_io_stats(self) -> Optional[Dict[str, Any]]:
        """获取网络I/O统计"""
        if self._should_update_cache():
            self._update_cache()
        return self._cache.get('network_io')
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有系统指标"""
        if self._should_update_cache():
            self._update_cache()
        
        return {
            'service': 'system',
            'cpu_usage': self._cache.get('cpu_usage'),
            'memory_usage': self._cache.get('memory_usage'),
            'disk_usage': self._cache.get('disk_usage'),
            'disk_io': self._cache.get('disk_io'),
            'network_io': self._cache.get('network_io'),
            'timestamp': self._cache.get('timestamp')
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统基本信息"""
        try:
            return {
                'platform': psutil.WINDOWS if psutil.WINDOWS else 'unix',
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 1),
                'boot_time': psutil.boot_time(),
                'python_version': psutil.version_info
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {}
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单测试psutil功能
            psutil.cpu_percent()
            psutil.virtual_memory()
            return True
        except Exception:
            return False


# 全局实例
system_metrics_service = SystemMetricsService()