from flask import Blueprint, jsonify
from ..services.instance_monitor_service import instance_monitor_service
import logging

logger = logging.getLogger(__name__)

monitor_bp = Blueprint('monitor', __name__)


@monitor_bp.post('/monitor/instances/check')
def check_instances_status():
    """
    手动触发所有实例状态检测
    """
    try:
        total, normal, error = instance_monitor_service.check_all_instances()
        
        return jsonify({
            'message': '实例状态检测完成',
            'total': total,
            'normal': normal,
            'error': error
        }), 200
        
    except Exception as e:
        logger.error(f"实例状态检测失败: {e}")
        return jsonify({'error': f'实例状态检测失败: {str(e)}'}), 500


@monitor_bp.get('/monitor/instances/summary')
def get_instances_summary():
    """
    获取实例状态汇总信息
    """
    try:
        summary = instance_monitor_service.get_instance_status_summary()
        return jsonify(summary), 200
        
    except Exception as e:
        logger.error(f"获取实例状态汇总失败: {e}")
        return jsonify({'error': f'获取实例状态汇总失败: {str(e)}'}), 500