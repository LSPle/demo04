import math
from typing import Dict, Any


"""
性能评分服务（大学生水平实现）

提供一个简单、可读的评分方法，根据已有的性能指标
计算总分（overall）以及几个分项分数：资源（resource）、
连接（connection）、查询（query）、缓存（cache）。

分数范围均为 0-100，值越高表示越好。
"""


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def compute_scores(performance: Dict[str, Any]) -> Dict[str, int]:
    """
    根据性能指标计算分数。

    期望的性能字段（尽量与现有接口保持一致）：
    - cpuUsage (%), memoryUsage (%), diskUsage (%)
    - currentConnections, maxConnections, lockWaits, deadlocks
    - avgQueryTime (ms), slowQueryRatio (%)
    - bufferPoolHitRate (%), sharedBufferHitRate (%)
    """

    # 资源分（CPU/内存/磁盘占用越高，分越低）
    cpu = _num(performance.get('cpuUsage'), 0)
    mem = _num(performance.get('memoryUsage'), 0)
    disk = _num(performance.get('diskUsage'), 0)
    resource_penalty = 0.4 * cpu + 0.4 * mem + 0.2 * disk
    resource_score = _clamp(100.0 - resource_penalty)

    # 连接分（连接占用、锁等待、死锁影响分数）
    cur_conn = _num(performance.get('currentConnections'), 0)
    max_conn = _num(performance.get('maxConnections'), 1000)
    conn_ratio = 0.0 if max_conn <= 0 else cur_conn / max_conn
    conn_base = 95.0 - conn_ratio * 60.0  # 占满时约 35 分，空闲约 95 分
    lock_waits = _num(performance.get('lockWaits'), 0)
    deadlocks = _num(performance.get('deadlocks'), 0)
    conn_penalty = min(lock_waits / 10.0, 15.0) + min(deadlocks * 5.0, 20.0)
    connection_score = _clamp(conn_base - conn_penalty)

    # 查询分（平均耗时和慢查询比例影响分数）
    avg_ms = _num(performance.get('avgQueryTime'), 0)
    slow_ratio = _num(performance.get('slowQueryRatio'), 0)
    query_score = 90.0
    if avg_ms > 100:
        query_score -= 20
    elif avg_ms > 50:
        query_score -= 10
    elif avg_ms < 20:
        query_score += 10

    if slow_ratio > 5:
        query_score -= 15
    elif slow_ratio > 2:
        query_score -= 10
    elif slow_ratio < 1:
        query_score += 5

    query_score = _clamp(query_score)

    # 缓存分（命中率越高越好，两个命中率平均；缺失则取 50）
    hit1 = performance.get('bufferPoolHitRate')
    hit2 = performance.get('sharedBufferHitRate')
    if hit1 is None and hit2 is None:
        cache_score = 50.0
    else:
        cache_vals = []
        if hit1 is not None:
            cache_vals.append(_num(hit1, 0))
        if hit2 is not None:
            cache_vals.append(_num(hit2, 0))
        cache_score = _clamp(sum(cache_vals) / max(1, len(cache_vals)))

    # 总分（加权平均）
    overall = (
        0.25 * resource_score +
        0.20 * connection_score +
        0.30 * query_score +
        0.25 * cache_score
    )

    return {
        'overall': int(round(_clamp(overall))),
        'resource': int(round(resource_score)),
        'connection': int(round(connection_score)),
        'query': int(round(query_score)),
        'cache': int(round(cache_score)),
    }