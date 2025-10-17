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
    q = Instance.query
    if user_id:
        q = q.filter_by(user_id=user_id)
    instance = q.filter_by(id=instance_id).first()
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
        # 兼容前端显示：补充 avg_time_ms 与 rows_examined 字段
        data = result or {}
        tops = list(data.get('ps_top') or [])
        formatted_tops = []
        for t in tops:
            item = dict(t or {})
            # 将 avg_latency_ms 同步为 avg_time_ms（ms）
            if 'avg_latency_ms' in item and 'avg_time_ms' not in item:
                item['avg_time_ms'] = item.get('avg_latency_ms')
            # 将 rows_examined_avg 同步为 rows_examined（平均扫描行数）
            if 'rows_examined_avg' in item and 'rows_examined' not in item:
                item['rows_examined'] = item.get('rows_examined_avg')
            formatted_tops.append(item)
        data['ps_top'] = formatted_tops
        return jsonify(data), 200
    else:
        return jsonify({'error': message}), 400

@slowlog_bp.get('/instances/<int:instance_id>/slowlog')
def list_slowlog(instance_id: int):
    """获取慢日志列表"""
    user_id = request.args.get('userId')
    
    # 查找实例
    q = Instance.query
    if user_id:
        q = q.filter_by(user_id=user_id)
    instance = q.filter_by(id=instance_id).first()
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
        # 兼容前端表格字段需求：query、count、avg_time_ms、rows_examined
        data = result or {}
        items = list(data.get('items') or [])
        formatted = []
        for it in items:
            q_sec = it.get('query_time')
            try:
                avg_ms = round(float(q_sec) * 1000, 2)
            except Exception:
                avg_ms = 0
            formatted.append({
                'query': it.get('sql_text') or it.get('query') or '',
                'count': 1,  # 表抽样为单条记录，次数记为1
                'avg_time_ms': avg_ms,
                'rows_examined': it.get('rows_examined', 0),
            })
        data['items'] = formatted
        return jsonify(data), 200
    else:
        return jsonify({'error': message}), 400