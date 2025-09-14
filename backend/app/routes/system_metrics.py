from flask import Blueprint, jsonify
from ..services.system_metrics_service import system_metrics_service
from ..services.prometheus_service import prometheus_service
import logging

logger = logging.getLogger(__name__)

system_metrics_bp = Blueprint('system_metrics', __name__)


@system_metrics_bp.get('/system-metrics/health')
def system_metrics_health():
    """检查系统指标采集服务健康状态"""
    try:
        psutil_ok = system_metrics_service.health_check()
        prometheus_ok = prometheus_service.health_check()
        
        return jsonify({
            'psutil_available': psutil_ok,
            'prometheus_available': prometheus_ok,
            'recommended': 'psutil' if psutil_ok else ('prometheus' if prometheus_ok else 'none'),
            'status': 'healthy' if (psutil_ok or prometheus_ok) else 'unhealthy'
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


@system_metrics_bp.get('/system-metrics/comparison')
def compare_metrics_sources():
    """对比psutil和Prometheus的指标采集结果"""
    try:
        result = {
            'psutil': None,
            'prometheus': None,
            'comparison': None
        }
        
        # 获取psutil指标
        if system_metrics_service.health_check():
            result['psutil'] = {
                'available': True,
                'metrics': system_metrics_service.get_all_metrics()
            }
        else:
            result['psutil'] = {
                'available': False,
                'error': 'psutil服务不可用'
            }
        
        # 获取Prometheus指标
        if prometheus_service.health_check():
            result['prometheus'] = {
                'available': True,
                'metrics': prometheus_service.get_all_metrics('mysqld')
            }
        else:
            result['prometheus'] = {
                'available': False,
                'error': 'Prometheus服务不可用'
            }
        
        # 简单对比
        if result['psutil']['available'] and result['prometheus']['available']:
            psutil_metrics = result['psutil']['metrics']
            prom_metrics = result['prometheus']['metrics']
            
            result['comparison'] = {
                'cpu_diff': abs((psutil_metrics.get('cpu_usage') or 0) - (prom_metrics.get('cpu_usage') or 0)),
                'memory_diff': abs((psutil_metrics.get('memory_usage') or 0) - (prom_metrics.get('memory_usage') or 0)),
                'recommendation': 'psutil更轻量，推荐优先使用'
            }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"指标对比失败: {e}")
        return jsonify({
            'error': f'指标对比失败: {str(e)}'
        }), 500