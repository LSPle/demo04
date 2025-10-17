'''
   基于 psutil 的本地系统指标采集接口
'''
from flask import Blueprint, jsonify
from ..services.system_metrics_service import system_metrics_service
import logging

logger = logging.getLogger(__name__)

system_metrics_bp = Blueprint('system_metrics', __name__)


@system_metrics_bp.get('/system-metrics/health')
def system_metrics_health():
    """检查系统指标采集服务健康状态"""
    try:
        psutil_ok = system_metrics_service.health_check()

        return jsonify({
            'psutil_available': psutil_ok,
            'status': 'healthy' if psutil_ok else 'unhealthy'
        }), 200
        
    except Exception as e:
        logger.error(f"系统指标健康检查失败: {e}")
        return jsonify({
            'error': f'健康检查失败: {str(e)}',
            'status': 'error'
        }), 500


@system_metrics_bp.get('/system-metrics/current')
def get_current_system_metrics():
    """获取当前系统指标（使用psutil）"""
    try:
        if not system_metrics_service.health_check():
            return jsonify({
                'error': 'psutil服务不可用',
                'suggestion': '请检查psutil依赖是否正确安装'
            }), 503
        
        metrics = system_metrics_service.get_all_metrics()
        system_info = system_metrics_service.get_system_info()
        
        return jsonify({
            'metrics': metrics,
            'system_info': system_info,
            'source': 'psutil',
            'timestamp': metrics.get('timestamp')
        }), 200
        
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
        return jsonify({
            'error': f'获取系统指标失败: {str(e)}'
        }), 500