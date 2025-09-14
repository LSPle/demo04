from flask import Blueprint, Response, current_app, request, stream_with_context, jsonify
import json
import time
import logging
from ..services.prometheus_service import prometheus_service
from ..models import Instance
from ..services.metrics_summary_service import metrics_summary_service

logger = logging.getLogger(__name__)

metrics_bp = Blueprint('metrics', __name__)


def sse_format(event: str = None, data: dict = None, id: str = None) -> str:
    """Format message for SSE"""
    parts = []
    if event:
        parts.append(f"event: {event}")
    if id:
        parts.append(f"id: {id}")
    if data is not None:
        parts.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    parts.append("\n")
    return "\n".join(parts)


@metrics_bp.get('/metrics/stream')
def stream_metrics():
    """SSE stream endpoint for real-time metrics"""
    service = request.args.get('service') or 'mysqld'  # default service label
    interval = int(request.args.get('interval', 5))

    # CORS for EventSource
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    }

    def generate():
        try:
            yield sse_format(event='open', data={'message': 'stream opened', 'service': service})
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while True:
                try:
                    metrics = prometheus_service.get_all_metrics(service)
                    yield sse_format(event='metrics', data=metrics, id=str(int(time.time())))
                    consecutive_errors = 0  # 重置错误计数
                except GeneratorExit:
                    logger.info(f"SSE stream closed for service: {service}")
                    break
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error getting metrics for {service}: {str(e)}")
                    
                    # 如果连续错误次数过多，发送错误事件并可能断开连接
                    if consecutive_errors >= max_consecutive_errors:
                        yield sse_format(event='error', data={
                            'message': f'连续获取指标失败，服务可能不可用: {str(e)}',
                            'consecutive_errors': consecutive_errors
                        })
                        logger.warning(f"Too many consecutive errors ({consecutive_errors}) for service {service}, continuing...")
                    else:
                        yield sse_format(event='error', data={
                            'message': str(e),
                            'consecutive_errors': consecutive_errors
                        })
                
                time.sleep(interval)
        except Exception as e:
            logger.error(f"SSE stream initialization error: {str(e)}")
            yield sse_format(event='error', data={'message': f'流初始化失败: {str(e)}'})

    return Response(stream_with_context(generate()), headers=headers)


@metrics_bp.get('/metrics/health')
def metrics_health():
    ok = prometheus_service.health_check()
    return jsonify({'prometheus_ok': ok}), (200 if ok else 500)


@metrics_bp.get('/instances/<int:instance_id>/metrics/summary')
def metrics_summary(instance_id: int):
    try:
        # 按 userId 过滤实例归属
        user_id = request.args.get('userId')
        q = Instance.query
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        inst = q.filter_by(id=instance_id).first()
        if not inst:
            return jsonify({'error': '实例不存在'}), 404
        data = metrics_summary_service.get_summary(inst)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"获取指标摘要失败: {e}")
        return jsonify({'error': f'获取指标摘要失败: {e}'}), 500