from flask import Blueprint, jsonify, request
import logging
import json
import time

from ..models import Instance
from ..services.metrics_summary_service import metrics_summary_service
from ..services.config_score_service import compute_scores
from ..services.deepseek_service import DeepSeekClient, strip_markdown

"""
配置优化路由

将原先散落在 metrics.py 中与“配置优化”相关的接口迁移到此文件：
- GET   /api/config/summary                      通用指标摘要（含评分）
- GET   /api/instances/<id>/config/summary      指定实例指标摘要（含评分）
- POST  /api/instances/<id>/config/advise       基于指标的配置优化建议（DeepSeek）

同时提供用于复用的构建函数，便于旧路由做兼容性委托调用。
"""

logger = logging.getLogger(__name__)

config_optimize_bp = Blueprint('config_optimize', __name__)


# -------- 复用构建函数（供路由与旧文件委托调用） -------- #

def build_general_config_summary():
    """构建通用系统指标摘要（不依赖特定实例）并计算评分"""
    try:
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
        # 增加配置优化评分计算
        try:
            score = compute_scores(data)
            data['score'] = score
        except Exception:
            # 评分计算失败时保持原有结构
            pass
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"获取通用指标摘要失败: {e}")
        return jsonify({'error': f'获取通用指标摘要失败: {e}'}), 500


def build_instance_config_summary(instance_id: int):
    """构建指定实例的指标摘要并计算评分（强制窗口采样，默认6秒）"""
    try:
        # 按 userId 过滤实例归属
        user_id = request.args.get('userId')
        q = Instance.query
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        inst = q.filter_by(id=instance_id).first()
        if not inst:
            return jsonify({'error': '实例不存在'}), 404

        # 强制窗口采样：读取 window_s，默认6秒
        window_s = request.args.get('window_s')
        window_int = 6
        try:
            if window_s is not None:
                window_int = max(1, int(window_s))
        except Exception:
            window_int = 6

        # 始终执行窗口采样摘要
        data = metrics_summary_service.get_summary_with_window(inst, window_int)

        # 增加配置优化评分计算
        try:
            score = compute_scores(data)
            data['score'] = score
        except Exception:
            pass
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"获取指标摘要失败: {e}")
        return jsonify({'error': f'获取指标摘要失败: {e}'}), 500


def build_instance_config_advise(instance_id: int):
    """根据指标摘要生成配置优化建议（DeepSeek），并附带评分"""
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
        # 增加配置优化评分计算，方便前端复用
        try:
            score = compute_scores(summary)
            summary['score'] = score
        except Exception:
            pass

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


# -------- 路由定义（对外暴露） -------- #

@config_optimize_bp.get('/config/summary')
def config_general_summary():
    return build_general_config_summary()


@config_optimize_bp.get('/instances/<int:instance_id>/config/summary')
def config_metrics_summary(instance_id: int):
    return build_instance_config_summary(instance_id)


@config_optimize_bp.post('/instances/<int:instance_id>/config/advise')
def config_metrics_advise(instance_id: int):
    return build_instance_config_advise(instance_id)