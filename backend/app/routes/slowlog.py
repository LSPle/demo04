from flask import Blueprint, jsonify, request
from ..models import Instance
from ..services.slowlog_service import slowlog_service

'''
    慢日志分析
'''

# 创建慢日志蓝图
slowlog_bp = Blueprint('slowlog', __name__)

@slowlog_bp.post('/instances/<int:instance_id>/slowlog/analyze')
def analyze_slowlog(instance_id: int):
    """慢日志分析"""
    user_id = request.args.get('userId')
    
    # 查找实例
    instance = Instance.query.filter_by(id=instance_id, user_id=user_id).first()
    if not instance:
        return jsonify({'error': '实例不存在'}), 404
    
    # 获取请求参数
    data = request.get_json() or {}
    top = data.get('top', 20)
    min_avg_ms = data.get('min_avg_ms', 10)
    tail_kb = data.get('tail_kb', 256)
    
    # 调用服务分析
    success, result, message = slowlog_service.analyze(instance, top=top, min_avg_ms=min_avg_ms, tail_kb=tail_kb)
    
    if success:
        return jsonify(result), 200
    else:
        return jsonify({'error': message}), 400

@slowlog_bp.get('/instances/<int:instance_id>/slowlog')
def list_slowlog(instance_id: int):
    """获取慢日志列表"""
    user_id = request.args.get('userId')
    
    # 查找实例
    instance = Instance.query.filter_by(id=instance_id, user_id=user_id).first()
    if not instance:
        return jsonify({'error': '实例不存在'}), 404
    
    # 获取查询参数
    page = request.args.get('page', '1')
    page_size = request.args.get('page_size', '10')
    keyword = request.args.get('keyword', '')
    user_host = request.args.get('user_host', '')
    db = request.args.get('db', '')
    start_time = request.args.get('start_time', '')
    end_time = request.args.get('end_time', '')
    
    filters = {
        'keyword': keyword,
        'user_host': user_host,
        'db': db,
        'start_time': start_time,
        'end_time': end_time,
    }
    
    # 调用服务获取数据
    success, result, message = slowlog_service.list_from_table(instance, page=page, page_size=page_size, filters=filters)
    
    if success:
        return jsonify(result), 200
    else:
        return jsonify({'error': message}), 400