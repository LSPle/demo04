from flask import Blueprint, jsonify, request, Response
import logging
import time
from typing import Any, Dict

from ..models import Instance
from ..services.metrics_summary_service import metrics_summary_service
from ..services.performance_score_service import compute_scores as compute_performance_scores
from ..services.architecture_advice_service import get_architecture_advice


logger = logging.getLogger(__name__)

arch_opt_bp = Blueprint('arch_optimize', __name__)


def _num(x, default=0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


@arch_opt_bp.post('/instances/<int:instance_id>/arch/analyze')
#架构优化分析
def analyze_architecture(instance_id: int):
    # 直接按实例ID查找，不进行 userId 过滤
    inst = Instance.query.filter_by(id=instance_id).first()
    if not inst:
        return jsonify({'error': '实例不存在'}), 404

    try:
        # 读取窗口参数，默认6秒
        # window_s = request.args.get('window_s')
        window_int = 6  # 默认6秒窗口
        # try:
        #     if window_s is not None:
        #         window_int = max(1, int(window_s))
        # except Exception:
        #     window_int = 6

        # 强制使用窗口采样，确保QPS/TPS数据准确性
        # summary: Dict[str, Any] = metrics_summary_service.get_summary_with_window(inst, window_int)
        summary = metrics_summary_service.get_summary_with_window(inst, window_int)


        #组装前端需要的性能数据结构
        system = summary.get('system', {})
        mysql = summary.get('mysql', {})
        perf = summary.get('perf', {})

        performance = {
            # 基础资源占用
            'version': getattr(inst, 'version', None) or '8.0.x',  # MySQL版本号
            'cpuUsage': _num(system.get('cpu_usage'), 0),          # CPU使用率
            'memoryUsage': _num(system.get('memory_usage'), 0),    # 内存使用率
            'diskUsage': _num(system.get('disk_usage'), 0),        # 磁盘使用率
            'networkIO': _num(system.get('network_io_mbps'), 0),   # 网络IO

            # 主从延迟
            # 保留 None 表示无数据，避免与真实 0ms 混淆
            'replicationDelay': (int(float(mysql.get('replication_delay_ms'))) if mysql.get('replication_delay_ms') is not None else None),

            # 连接相关
            'activeConnections': int(_num(mysql.get('threads_running'), 0)),      # 活跃连接数
            'currentConnections': int(_num(mysql.get('threads_connected'), 0)),   # 当前连接数
            'maxConnections': int(_num(mysql.get('max_connections'), 1000)),      # 最大连接数
            'peakConnections': int(_num(mysql.get('peak_connections'), _num(mysql.get('threads_connected'), 0))),  # 峰值连接数
            'transactionCount': int(_num(mysql.get('transactions_total'), 0)),    # 事务总数

            # 锁和并发控制
            'lockWaits': int(_num(mysql.get('innodb_row_lock_waits'), 0)),        # 行锁等待次数
            'deadlocks': int(_num(mysql.get('deadlocks'), 0)),                    # 死锁次数

            # 缓存命中率
            'bufferPoolHitRate': _num(mysql.get('cache_hit_rate'), 0),            # InnoDB缓冲池命中率
            'sharedBufferHitRate': _num(mysql.get('cache_hit_rate'), 0),          # 共享缓冲命中率

            # 查询性能
            'qps': _num(perf.get('qps'), 0),                                      # 每秒查询数
            'slowQueryEnabled': mysql.get('slow_query_ratio') is not None,        # 是否启用慢查询日志
            'slowestQuery': _num(perf.get('slowest_query_ms'), 0),               # 最慢查询时间(ms)
            'slowQueryRatio': _num(mysql.get('slow_query_ratio'), 0),            # 慢查询比例(%)
            'avgQueryTime': _num(mysql.get('avg_response_time_ms'), 0)           # 平均查询时间(ms)
        }

        # 算分数（总分 + 分项分数）
        scores = {}
        # try:
        scores = compute_performance_scores(performance)
        # except Exception:
            # 评分兜底，避免接口失败
            # scores = {'overall': 60, 'resource': 60, 'connection': 60, 'query': 60, 'cache': 60}

        # 构建返回结果
        result = {
            'instance': {
                'id': inst.id,
                'instanceName': inst.instance_name,
                'dbType': 'mysql',
                'host': inst.host,
                'port': inst.port,
            },
            'performance': performance,
            'score': scores,
            'generated_at': int(time.time())
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"架构分析失败: {e}")
        return jsonify({'error': f'分析失败: {e}'}), 500


@arch_opt_bp.post('/instances/<int:instance_id>/arch/advise')
def advise_architecture(instance_id: int):
    try:
        data = request.get_json(silent=True) or {}
        content = get_architecture_advice(None, override=data)
        if not content:
            return jsonify({'error': 'LLM分析失败'}), 500

        return Response(content, mimetype='text/plain')
    except Exception as e:
        return jsonify({'error': f'分析失败: {e}'}), 500

@arch_opt_bp.post('/instances/<int:instance_id>/arch/advice')
def advise_architecture_alias(instance_id: int):
    return advise_architecture(instance_id)
