import math
from typing import Dict, Any


"""
性能评分服务

提供一个简单、可读的评分方法，根据已有的性能指标
计算总分（overall）以及几个分项分数：资源（resource）、
连接（connection）、查询（query）、缓存（cache）。

分数范围均为 0-100，值越高表示越好。
"""

#转换为浮点数
def to_num(x: Any, default: float = 0.0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

# 对值进行限制，确保在 [low, high] 范围内(保险)
def clamp_value(value: float, low: float = 0.0, high: float = 100.0):
    return max(low, min(high, value))


def compute_scores(performance: Dict[str, Any]):
    """
    根据性能指标计算分数。

    期望的性能字段（尽量与现有接口保持一致）：
    - cpuUsage (%), memoryUsage (%), diskUsage (%)
    - currentConnections, maxConnections, lockWaits, deadlocks
    - avgQueryTime (ms), slowQueryRatio (%)
    - bufferPoolHitRate (%), sharedBufferHitRate (%)
    """

    # 资源分（CPU/内存/磁盘占用越高，分越低）
    cpu = to_num(performance.get('cpuUsage'), 0)        # 获取CPU使用率，默认0
    mem = to_num(performance.get('memoryUsage'), 0)     # 获取内存使用率，默认0
    disk = to_num(performance.get('diskUsage'), 0)      # 获取磁盘使用率，默认0
    resource_penalty = 0.4 * cpu + 0.4 * mem + 0.2 * disk  # 计算资源扣分：CPU和内存权重各40%，磁盘20%
    resource_score = clamp_value(100.0 - resource_penalty)  # 资源得分 = 100 - 扣分，限制在0-100范围！

    # 连接分（连接占用、锁等待、死锁影响分数）
    cur_conn = to_num(performance.get('currentConnections'), 0)    # 当前连接数
    max_conn = to_num(performance.get('maxConnections'), 1000)     # 最大连接数，默认1000
    conn_ratio = 0.0 if max_conn <= 0 else cur_conn / max_conn    # 连接占用比例
    conn_base = 100.0 - conn_ratio * 60.0                          # 基础连接分：占满时40分，空闲时100分
    lock_waits = to_num(performance.get('lockWaits'), 0)           # 锁等待次数
    deadlocks = to_num(performance.get('deadlocks'), 0)            # 死锁次数
    conn_penalty = min(lock_waits / 10.0, 20.0) + min(deadlocks * 5.0, 20.0)  # 连接扣分：锁等待最多扣20分，死锁最多扣20分
    connection_score = clamp_value(conn_base - conn_penalty)       # 连接得分 = 基础分 - 扣分

    avg_ms = to_num(performance.get('avgQueryTime'), 0)
    slow_ratio = to_num(performance.get('slowQueryRatio'), 0)
    L_REF = 200.0
    S_REF = 10.0
    lat_penalty = min(60.0, (avg_ms / L_REF) * 60.0)
    slow_penalty = min(40.0, (slow_ratio / S_REF) * 40.0)
    query_score = clamp_value(100.0 - lat_penalty - slow_penalty)

    # 缓存分（命中率越高越好，两个命中率平均；缺失则取 50）
    hit1 = performance.get('bufferPoolHitRate')
    hit2 = performance.get('sharedBufferHitRate')
    if hit1 is None and hit2 is None:
        cache_score = 50.0
    else:
        cache_vals = []
        if hit1 is not None:
            cache_vals.append(to_num(hit1, 0))
        if hit2 is not None:
            cache_vals.append(to_num(hit2, 0))
        cache_score = clamp_value(sum(cache_vals) / max(1, len(cache_vals)))

    # 总分（加权平均）
    """
    加权平均计算总分：
    - 资源分（25%）
    - 连接分（20%）
    - 查询分（30%）
    - 缓存分（25%）

    查询性能30%最高 ：因为查询速度是数据库性能的核心指标，直接影响用户体验。
    资源使用25% 和 缓存效率25% ：系统资源和缓存都是性能基础，同等重要。
    连接管理20%最低 ：主要影响并发能力，相对次要
    """
    overall = (
        0.25 * resource_score +
        0.20 * connection_score +
        0.30 * query_score +
        0.25 * cache_score
    )

    return {
        'overall': int(round(clamp_value(overall))),
        'resource': int(round(resource_score)),
        'connection': int(round(connection_score)),
        'query': int(round(query_score)),
        'cache': int(round(cache_score)),
    }