from flask import Blueprint, jsonify, request
from ..services.instance_monitor_service import instance_monitor_service
import logging

'''
    实例监控(刷新按钮)
'''

logger = logging.getLogger(__name__)

monitor_bp = Blueprint('monitor', __name__)


@monitor_bp.post('/monitor/instances/check')
def check_instances_status():
    """
    手动触发实例状态检测
    支持按用户ID过滤：POST请求体中包含userId参数则只检测该用户的实例
    """
    try:
        # 从请求体中获取userId参数
        data = request.get_json() or {}
        user_id = data.get('userId')
        
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
        summary = instance_monitor_service.get_instance_status_summary() #调用services/instance_monitor_service获取实例
        return jsonify(summary), 200
        
    except Exception as e:
        logger.error(f"获取实例状态汇总失败: {e}")
        return jsonify({'error': f'获取实例状态汇总失败: {str(e)}'}), 500