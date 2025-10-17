from flask import Blueprint, jsonify, request
import logging
import time
from typing import Any, Dict

from ..models import Instance
from ..services.metrics_summary_service import metrics_summary_service
from ..services.direct_mysql_metrics_service import direct_mysql_metrics_service
from ..services.performance_score_service import compute_scores as compute_performance_scores


"""
架构优化（最小可行版）

以大学生代码水平实现一个简单的后端接口：
- 路由：POST /api/instances/<id>/arch/analyze
- 功能：聚合已有服务的关键指标，做一些朴素的风险判断，
        返回给前端使用的性能数据和建议。

说明：
- 只调用项目中已有的服务，不新增复杂逻辑或外部依赖。
- 指标缺失时返回 None 或合理的默认值，保证接口稳定。
"""

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
def analyze_architecture(instance_id: int):
    """架构优化分析（最小可行版）"""
    user_id = request.args.get('userId')

    # 1) 查找实例
    inst = Instance.query.filter_by(id=instance_id, user_id=user_id).first()
    if not inst:
        return jsonify({'error': '实例不存在'}), 404

    try:
        # 2) 采集指标（复用已有服务）
        summary: Dict[str, Any] = metrics_summary_service.get_summary(inst)
        direct: Dict[str, Any] = direct_mysql_metrics_service.get_all_direct_metrics(inst)

        # 3) 组装前端需要的性能数据结构（尽量贴近前端字段）
        system = summary.get('system', {})
        mysql = summary.get('mysql', {})
        perf = summary.get('perf', {})

        performance = {
            # 基础资源占用
            'version': getattr(inst, 'version', None) or '8.0.x',
            'cpuUsage': _num(system.get('cpu_usage'), 0),
            'memoryUsage': _num(system.get('memory_usage'), 0),
            'diskUsage': _num(system.get('disk_usage'), 0),
            'networkIO': _num(system.get('network_io_mbps'), 0),

            # 主从延迟
            # 保留 None 表示无数据，避免与真实 0ms 混淆
            'replicationDelay': (int(float(mysql.get('replication_delay_ms'))) if mysql.get('replication_delay_ms') is not None else None),

            # 连接相关
            'activeConnections': int(_num(mysql.get('threads_running'), 0)),
            'currentConnections': int(_num(mysql.get('threads_connected'), 0)),
            'maxConnections': int(_num(mysql.get('max_connections'), 1000)),
            'peakConnections': int(_num(mysql.get('peak_connections'), _num(mysql.get('threads_connected'), 0))),
            'transactionCount': int(_num(direct.get('transactions_total', mysql.get('transactions_total')), 0)),

            # 锁和并发控制
            'lockWaits': int(_num(mysql.get('innodb_row_lock_waits'), 0)),
            'deadlocks': int(_num(mysql.get('deadlocks'), 0)),

            # 缓存命中率
            'bufferPoolHitRate': _num(mysql.get('cache_hit_rate'), 0),
            'sharedBufferHitRate': _num(mysql.get('cache_hit_rate'), 0),  # 共享缓冲命中率暂无，复用同值

            # 查询性能
            'qps': _num(perf.get('qps', direct.get('qps')), 0),
            'slowQueryEnabled': direct.get('slow_query_ratio') is not None,
            'slowestQuery': _num(perf.get('slowest_query_ms'), 0),
            'slowQueryRatio': _num(mysql.get('slow_query_ratio', direct.get('slow_query_ratio')), 0),
            'avgQueryTime': _num(mysql.get('avg_response_time_ms', direct.get('avg_response_time_ms')), 0)
        }

        # 4) 计算分数（总分 + 分项分数）
        scores = {}
        try:
            scores = compute_performance_scores(performance)
        except Exception:
            # 评分兜底，避免接口失败
            scores = {'overall': 60, 'resource': 60, 'connection': 60, 'query': 60, 'cache': 60}

        # 5) 朴素风险识别（简单规则）
        risks = []
        try:
            # 连接压力
            conn = performance['currentConnections'] / max(1, performance['maxConnections'])
            if conn > 0.8:
                risks.append('连接占用超过80%，可能存在连接压力')

            # 缓存命中率
            if performance['bufferPoolHitRate'] and performance['bufferPoolHitRate'] < 90:
                risks.append('InnoDB 缓冲命中率较低，建议增加缓冲池或优化查询')

            # 慢查询比例
            if performance['slowQueryRatio'] and performance['slowQueryRatio'] > 2:
                risks.append('慢查询比例偏高，建议优化索引或重写 SQL')

            # 平均查询耗时
            if performance['avgQueryTime'] and performance['avgQueryTime'] > 100:
                risks.append('平均查询耗时较高，注意索引设计与表结构优化')
        except Exception:
            # 规则兜底，避免接口失败
            pass

        # 6) 简单建议（基于风险点给出对应建议）
        advice = []
        if any('连接占用' in r for r in risks):
            advice.append({'title': '连接池配置优化', 'description': '适当提高最大连接数或引入连接池，减少连接争用', 'priority': '中'})
        if any('命中率较低' in r for r in risks):
            advice.append({'title': '缓冲池优化', 'description': '增加 Innodb 缓冲池大小，并检查热点表/索引', 'priority': '中'})
        if any('慢查询比例偏高' in r for r in risks):
            advice.append({'title': '慢查询治理', 'description': '对慢 SQL 建立合适索引，避免全表扫描；必要时重写 SQL', 'priority': '高'})
        if any('平均查询耗时较高' in r for r in risks):
            advice.append({'title': '查询性能优化', 'description': '检查执行计划与表统计信息，优化索引选择与JOIN策略', 'priority': '高'})

        if not advice:
            advice.append({'title': '总体良好', 'description': '当前未发现明显风险，可持续观察与按需优化', 'priority': '低'})

        result = {
            'instance': {
                'id': inst.id,
                'instanceName': inst.instance_name if hasattr(inst, 'instance_name') else getattr(inst, 'instanceName', ''),
                'dbType': getattr(inst, 'db_type', None) or getattr(inst, 'dbType', None) or 'mysql',
                'host': inst.host,
                'port': inst.port,
            },
            'performance': performance,
            'score': scores,
            'risks': risks,
            'advice': advice,
            'generated_at': int(time.time())
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"架构分析失败: {e}")
        return jsonify({'error': f'分析失败: {e}'}), 500