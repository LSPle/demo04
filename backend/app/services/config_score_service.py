from typing import Dict, Any

"""
配置优化评分服务

用途：为“配置优化”页面或后端分析逻辑提供一个简单、可读、可解释的评分方法。
输入：metrics_summary_service.get_summary(inst) 的返回结构（包含 system/mysql/perf 三类关键指标）。
输出：总分 overall 以及分项分数（system/mysql/performance/security），范围 0~100，值越高越好。

设计思路：
- 分维度评分：系统资源（CPU/内存/磁盘/IO）、MySQL配置与运行（连接压力/缓存命中/慢比/响应/锁/索引）、性能（QPS/TPS/P95/Redo）、安全/稳定（如复制延迟简单纳入）。
- 阈值与线性扣分结合：便于理解与微调，符合“大学生项目”可讲解性。
- 统一单位与容错处理：百分比支持 0~1 与 0~100 两种表示；缺失值使用温和默认值避免崩溃。
"""


def to_num(x: Any, default: float = 0.0):
    """将任意输入安全转换为 float。缺失或异常返回默认值。"""
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def clamp_value(value: float, low: float = 0.0, high: float = 100.0):
    """限制到 [low, high] 范围。"""
    return max(low, min(high, value))


def to_percentage(x: Any, default: float = 0.0):
    """
    转换为 0~100 的百分比。
    - 若输入在 0~1 之间，视为比例并乘以 100。
    - 若输入在 0~100 之间，视为百分比直接使用。
    - 其他值做基本容错并截断到 0~100。
    """
    n = to_num(x, default)
    if 0.0 <= n <= 1.0:
        return clamp_value(n * 100.0)
    return clamp_value(n)


def compute_scores(summary: Dict[str, Any]):
    """
    计算配置优化总分与分项分数。

    参数：
    - summary: metrics_summary_service.get_summary(inst) 的返回字典，包含：
      - system: { cpu_usage, memory_usage, disk_usage, network_io_mbps }
      - mysql:  { threads_running, max_connections, cache_hit_rate, slow_query_ratio,
                 avg_response_time_ms, innodb_row_lock_time_ms, deadlocks,
                 index_usage_rate, replication_delay_ms }
      - perf:   { qps, tps, p95_latency_ms, io_latency_ms, redo_write_latency_ms }

    返回：
    - { overall, system, mysql, performance, security } 均为整数 0~100。
    """
    sys = summary.get('system', {})
    mysql = summary.get('mysql', {})
    perf = summary.get('perf', {})

    # 1) 系统评分：CPU/内存/磁盘占用越高越扣分；IO延迟作为轻量扣分项
    cpu = to_percentage(sys.get('cpu_usage'), 0.0)
    mem = to_percentage(sys.get('memory_usage'), 0.0)
    disk = to_percentage(sys.get('disk_usage'), 0.0)
    io_lat = to_num(perf.get('io_latency_ms'), 0.0)

    # 线性扣分 + 阈值扣分（简单易懂）
    sys_penalty = 0.4 * cpu + 0.4 * mem + 0.2 * disk
    if io_lat > 50:
        sys_penalty += 15
    elif io_lat > 20:
        sys_penalty += 8
    elif io_lat > 10:
        sys_penalty += 4
    system_score = clamp_value(100.0 - sys_penalty)

    # 2) MySQL评分：连接压力、缓存命中、慢查询比例、平均响应、锁等待/死锁、索引使用率
    threads = to_num(mysql.get('threads_running'), 0.0)
    max_conn = to_num(mysql.get('max_connections'), 100.0)
    conn_ratio = threads / max_conn if max_conn > 0 else 0.0  # 0~1

    hit = to_percentage(mysql.get('cache_hit_rate'), 0.0)
    slow_ratio = to_percentage(mysql.get('slow_query_ratio'), 0.0)
    avg_ms = to_num(mysql.get('avg_response_time_ms'), 0.0)
    lock_ms = to_num(mysql.get('innodb_row_lock_time_ms'), 0.0)
    deadlocks = to_num(mysql.get('deadlocks'), 0.0)
    index_rate = to_percentage(mysql.get('index_usage_rate'), 100.0)  # 缺失视为 100（不扣分）

    mysql_score = 90.0
    # 连接压力：占满时扣至 ~65 分；空闲影响较小
    mysql_score -= min(conn_ratio * 35.0, 25.0)

    # 缓存命中率：偏低扣分，极高略增分
    if hit < 80:
        mysql_score -= 10
    elif hit < 90:
        mysql_score -= 5
    elif hit >= 95:
        mysql_score += 3

    # 慢查询比例（百分比）：高慢比明显扣分，低慢比加少量分
    if slow_ratio > 5:
        mysql_score -= 10
    elif slow_ratio > 2:
        mysql_score -= 6
    elif slow_ratio < 1:
        mysql_score += 4

    # 平均响应时间：高延迟扣分，低延迟加少量分
    if avg_ms > 100:
        mysql_score -= 12
    elif avg_ms > 50:
        mysql_score -= 6
    elif avg_ms < 20:
        mysql_score += 4

    # 锁等待与死锁：线性上限扣分，避免异常值导致过度扣分
    mysql_score -= min(lock_ms / 20.0, 10.0)
    mysql_score -= min(deadlocks * 5.0, 15.0)

    # 索引使用率：过低扣分，较高略增分
    if index_rate < 70:
        mysql_score -= 8
    elif index_rate < 85:
        mysql_score -= 4
    else:
        mysql_score += 2

    mysql_score = clamp_value(mysql_score)

    # 3) 性能评分：QPS/TPS（高略增分），P95/Redo 延迟（高扣分）
    qps = to_num(perf.get('qps'), 0.0)
    tps = to_num(perf.get('tps'), 0.0)
    p95 = to_num(perf.get('p95_latency_ms'), 0.0)
    redo = to_num(perf.get('redo_write_latency_ms'), 0.0)

    performance_score = 85.0
    # P95 延迟
    if p95 > 50:
        performance_score -= 20
    elif p95 > 30:
        performance_score -= 10
    elif p95 > 20:
        performance_score -= 5

    # Redo/WAL 写入延迟
    if redo > 10:
        performance_score -= 12
    elif redo > 5:
        performance_score -= 6

    # QPS/TPS 简单加分（仅作正向提示，避免夸张）
    if qps > 1000:
        performance_score += 5
    elif qps > 500:
        performance_score += 2
    if tps > 800:
        performance_score += 5
    elif tps > 400:
        performance_score += 2

    performance_score = clamp_value(performance_score)

    # 4) 安全/稳定评分（占比较小）：示例使用复制延迟（若无复制，默认良好）
    repl_delay = to_num(mysql.get('replication_delay_ms'), 0.0)
    security_score = 85.0
    if repl_delay > 5000:
        security_score -= 20
    elif repl_delay > 1000:
        security_score -= 10
    security_score = clamp_value(security_score)

    # 5) 总分加权（可按业务调整）
    overall = (
        0.25 * system_score +
        0.35 * mysql_score +
        0.30 * performance_score +
        0.10 * security_score
    )

    return {
        'overall': int(round(clamp_value(overall))),
        'system': int(round(system_score)),
        'mysql': int(round(mysql_score)),
        'performance': int(round(performance_score)),
        'security': int(round(security_score)),
    }


# 备注：如需兼容架构优化页面的旧字段（如 cpuUsage/memoryUsage/avgQueryTime 等），
# 可在调用层进行字段映射，或单独实现一个适配器函数，将旧结构转换到 summary 格式后复用本方法。