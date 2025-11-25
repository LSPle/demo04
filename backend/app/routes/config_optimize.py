from flask import Blueprint, jsonify, request, Response
import logging
import json
import time

from ..models import Instance
from ..services.metrics_summary_service import metrics_summary_service
from ..services.config_score_service import compute_scores
from ..services.config_advice_service import get_config_advice



logger = logging.getLogger(__name__)

config_optimize_bp = Blueprint('config_optimize', __name__)


# 获取一般指标摘要
def general_config_summary():
   
    try:
        inst = Instance.query.first()
        if not inst:
            return jsonify({'error': '未找到数据库实例'}), 404

        data = metrics_summary_service.get_summary_with_window(inst, 6)
        # 增加配置优化评分计算
        try:
            score = compute_scores(data)
            data['score'] = score
        except Exception:
            # 评分计算失败时保持原有结构
            pass
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': f'获取通用指标摘要失败: {e}'}), 500

# 构建指定实例的指标摘要并计算评分（强制窗口采样，默认6秒）
def build_instance_config_summary(instance_id: int):
    try:
        # 直接按实例ID查找，不进行 userId 过滤
        inst = Instance.query.filter_by(id=instance_id).first()
        if not inst:
            return jsonify({'error': '实例不存在'}), 404


        # 始终执行窗口采样摘要
        data = metrics_summary_service.get_summary_with_window(inst, 6)

        # 增加配置优化评分计算
        try:
            score = compute_scores(data)
            data['score'] = score
        except Exception:
            pass
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': f'获取指标摘要失败: {e}'}), 500


def build_instance_config_advise(instance_id: int):
    """根据指标摘要生成配置优化建议（DeepSeek），并附带评分（窗口采样）"""
    try:
        # 直接按实例ID查找，不进行 userId 过滤
        inst = Instance.query.filter_by(id=instance_id).first()
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

        # 获取窗口采样的指标摘要
        summary = metrics_summary_service.get_summary_with_window(inst, window_int)
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

        return jsonify({
            'metrics': summary,
            'advice': None,
            'error': 'DeepSeek未配置'
        }), 200

    except Exception as e:
        logger.error(f"生成配置优化建议失败: {e}")
        return jsonify({'error': f'生成配置优化建议失败: {e}'}), 500


# -------- 路由定义（对外暴露） -------- #

@config_optimize_bp.get('/config/summary')
def config_general_summary():
    return general_config_summary()


@config_optimize_bp.get('/instances/<int:instance_id>/config/summary')
def config_metrics_summary(instance_id: int):
    return build_instance_config_summary(instance_id)


@config_optimize_bp.post('/instances/<int:instance_id>/config/advise')
def config_metrics_advise(instance_id: int):
    return build_instance_config_advise(instance_id)


@config_optimize_bp.post('/instances/<int:instance_id>/config/advice')
def config_metrics_advice(instance_id: int):
    try:
        data = request.get_json(silent=True) or {}
        content = get_config_advice(None, override=data)
        if not content:
            return jsonify({'error': 'LLM分析失败'}), 500
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return jsonify({'error': f'分析失败: {e}'}), 500
