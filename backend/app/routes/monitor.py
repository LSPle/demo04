from flask import Blueprint, jsonify, request
from ..services.instance_monitor_service import instance_monitor_service
import logging

'''
    实例监控(刷新按钮)
'''

logger = logging.getLogger(__name__)

monitor_bp = Blueprint('monitor', __name__)

# 手动触发实例状态检测
@monitor_bp.post('/monitor/instances/check')
def check_instances_status():
    try:
        data = request.get_json() or {}
        # 当前方案不落库且不区分用户，后续可按userId过滤
        total, normal, error, statuses = instance_monitor_service.check_all_instances()
        return jsonify({
            'message': '实例状态检测完成',
            'total': total,
            'normal': normal,
            'error': error,
            'statuses': statuses
        }), 200
    except Exception as e:
        logger.error(f"实例状态检测失败: {e}")
        return jsonify({'error': f'实例状态检测失败: {str(e)}'}), 500


# @monitor_bp.get('/monitor/instances/summary')
# def get_instances_summary():
#     """
#     获取实例状态汇总信息（基于实时检测）
#     """
#     try:
#         summary = instance_monitor_service.get_instance_status_summary()
#         return jsonify(summary), 200
#     except Exception as e:
#         logger.error(f"获取实例状态汇总失败: {e}")
#         return jsonify({'error': f'获取实例状态汇总失败: {str(e)}'}), 500