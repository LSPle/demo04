from math import log
from flask import Blueprint, Response, current_app, request, stream_with_context, jsonify
import json
import time
import logging
from ..services.prometheus_service import prometheus_service
from ..models import Instance
from ..services.metrics_summary_service import metrics_summary_service
from ..services.deepseek_service import DeepSeekClient, strip_markdown

#实时指标流

logger = logging.getLogger(__name__)

metrics_bp = Blueprint('metrics', __name__)

'''
    获取指标(配置优化)，DeepSeek分析
'''
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


@metrics_bp.get('/metrics/summary')
def general_metrics_summary():
    """获取通用系统指标摘要（不依赖特定实例）"""
    try:
        # 尝试获取第一个可用的实例，如果没有则使用虚拟实例
        from ..models import Instance
        inst = Instance.query.first()
        
        if not inst:
            # 创建一个虚拟实例对象用于获取系统级指标
            class MockInstance:
                def __init__(self):
                    self.host = '192.168.112.128'
                    self.port = 3306
                    self.username = 'root'
                    self.password = '123456'
                    self.database = 'mysql'
            
            inst = MockInstance()
        
        data = metrics_summary_service.get_summary(inst)
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"获取通用指标摘要失败: {e}")
        return jsonify({'error': f'获取通用指标摘要失败: {e}'}), 500


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


@metrics_bp.post('/instances/<int:instance_id>/metrics/advise')
def metrics_advise(instance_id: int):
    """根据指标摘要生成配置优化建议（DeepSeek）。"""
    try:
        # 按 userId 过滤实例归属
        user_id = request.args.get('userId')
        q = Instance.query
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        inst = q.filter_by(id=instance_id).first()
        if not inst:
            return jsonify({'error': '实例不存在'}), 404

        # 获取指标摘要
        summary = metrics_summary_service.get_summary(inst)
        # logger.info(f"获取到的指标摘要: {summary}")

        # 预设提示词模板（配置优化页面）
        system_prompt = (
            "你是资深数据库性能和配置优化专家。基于给定的运行指标，提供简洁、可执行的配置层面优化建议。"
            "注意：不要输出多余的Markdown格式（如标题、代码块、粗体等）。直接给出中文要点列表。"
        )

        # 组装 12 项核心指标（缺失项以 N/A 填充）
        def _gv(d, *keys, default='N/A'):
            cur = d
            for k in keys:
                if not isinstance(cur, dict) or k not in cur:
                    return default
                cur = cur[k]
            return cur if (cur is not None and cur != '') else default

        metrics_12 = {
            'CPU利用率': _gv(summary, 'system', 'cpu_usage'),
            '内存使用率': _gv(summary, 'system', 'memory_usage'),
            '缓存命中率': _gv(summary, 'mysql', 'cache_hit_rate'),
            '磁盘I/O延迟(ms)': _gv(summary, 'perf', 'io_latency_ms'),
            '活跃连接数': _gv(summary, 'mysql', 'threads_running'),
            'QPS': _gv(summary, 'perf', 'qps'),
            'TPS': _gv(summary, 'perf', 'tps'),
            '慢查询比例': _gv(summary, 'mysql', 'slow_query_ratio'),
            '平均响应时间(ms)': _gv(summary, 'mysql', 'avg_response_time_ms'),
            'P95时延(ms)': _gv(summary, 'perf', 'p95_latency_ms'),
            '锁等待时间(ms)': _gv(summary, 'mysql', 'innodb_row_lock_time_ms'),
            '死锁次数': _gv(summary, 'mysql', 'deadlocks'),
            'Redo/WAL写入延迟(ms)': _gv(summary, 'perf', 'redo_write_latency_ms'),
            '索引使用率': _gv(summary, 'mysql', 'index_usage_rate'),
        }

        # 构造用户提示内容
        lines = [
            f"实例: {inst.instance_name} ({inst.host}:{inst.port})",
            "关键指标："
        ]
        for k, v in metrics_12.items():
            lines.append(f"- {k}: {v}")
        user_prompt = "\n".join(lines)

        client = DeepSeekClient()
        if not getattr(client, 'enabled', True) or not getattr(client, 'api_key', None):
            # 未配置 DeepSeek 时返回空建议，供前端降级显示
            return jsonify({
                'metrics': summary,
                'advice': None,
                'error': 'DeepSeek未配置'
            }), 200

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            resp_text = client._make_api_call(messages)
            cleaned = strip_markdown(resp_text or '')
            # 再做一次轻量净化：压缩多余空行
            import re
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
            return jsonify({
                'metrics': summary,
                'advice': cleaned,
                'error': None
            }), 200
        except Exception as e:
            logger.error(f"DeepSeek 分析失败: {e}")
            return jsonify({
                'metrics': summary,
                'advice': None,
                'error': f'DeepSeek分析失败: {e}'
            }), 200

    except Exception as e:
        logger.error(f"生成配置优化建议失败: {e}")
        return jsonify({'error': f'生成配置优化建议失败: {e}'}), 500