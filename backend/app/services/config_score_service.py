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

    # MySQL配置评分：从100分开始，只扣分不加分
    mysql_score = 100.0
    
    # 连接压力：连接使用率过高时扣分（超过80%才开始扣分）
    if conn_ratio > 0.8:
        # (conn_ratio - 0.8) 范围是 0~0.2，乘以 100 后范围是 0~20
        mysql_score -= (conn_ratio - 0.8) * 100.0

    # 缓存命中率：命中率低时扣分
    if hit < 80:
        mysql_score -= 15  # 命中率很低，扣15分
    elif hit < 90:
        mysql_score -= 8   # 命中率偏低，扣8分

    # 慢查询比例：慢查询过多时扣分
    # 毕设演示场景放宽阈值：因为总查询基数小，容易出现高比例
    if slow_ratio > 25:
        mysql_score -= 15  # 慢查询严重（>25%），扣15分
    elif slow_ratio > 10:
        mysql_score -= 8   # 慢查询偏多（>10%），扣8分

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
    # 毕设场景：小表可能倾向全表扫描，大幅降低扣分阈值
    if index_rate < 30:
        mysql_score -= 8   # 极低（<30%），扣8分
    elif index_rate < 50:
        mysql_score -= 4   # 较低（<50%），扣4分
    else:
        mysql_score += 2   # >=50% 视为及格，加2分

    mysql_score = clamp_value(mysql_score)

    # 3) 性能评分：QPS/TPS（高略增分），P95/Redo 延迟（高扣分）
    qps = to_num(perf.get('qps'), 0.0)
    tps = to_num(perf.get('tps'), 0.0)
    p95 = to_num(perf.get('p95_latency_ms'), 0.0)
    redo = to_num(perf.get('redo_write_latency_ms'), 0.0)

    # 性能评分：从100分开始，只扣分不加分
    performance_score = 100.0
    
    # P95 延迟：延迟过高时扣分（加大力度，确保极差情况能扣到0分）
    if p95 > 500:
        performance_score -= 60  # 严重卡顿（>500ms），直接扣60分
    elif p95 > 200:
        performance_score -= 40  # 明显卡顿（>200ms），扣40分
    elif p95 > 50:
        performance_score -= 20  # 轻微卡顿（>50ms），扣20分

    # Redo/WAL 写入延迟：写入延迟过高时扣分
    if redo > 50:
        performance_score -= 40  # 磁盘严重瓶颈（>50ms），扣40分
    elif redo > 20:
        performance_score -= 20  # 磁盘瓶颈（>20ms），扣20分
    elif redo > 10:
        performance_score -= 10  # 磁盘略慢（>10ms），扣10分

    performance_score = clamp_value(performance_score)

    # 4) 安全/稳定评分（占比较小）：示例使用复制延迟（若无复制，默认良好）
    repl_delay = to_num(mysql.get('replication_delay_ms'), 0.0)
    security_score = 100.0
    if repl_delay > 5000:
        security_score -= 20
    elif repl_delay > 1000:
        security_score -= 10
    security_score = clamp_value(security_score)

    # 5) 总分加权（可按业务调整）
    # 配置优化总分（加权平均）- MySQL配置最重要
    """
    MySQL配置35%最高 ：因为这是数据库优化项目的核心，配置参数直接影响数据库性能。
    性能表现30%次之 ：配置优化的最终目标就是提升性能，需要重点关注。
    系统配置25% 和 安全配置10% ：系统层面配置也重要但相对次要。
    """
    overall = (
        system_score * 0.25 +        # 系统配置：25%
        mysql_score * 0.35 +         # MySQL配置：35%（最重要）
        performance_score * 0.30 +   # 性能表现：30%
        security_score * 0.10        # 安全配置：10%
    )

    return {
        'overall': int(round(clamp_value(overall))),
        'system': int(round(system_score)),
        'mysql': int(round(mysql_score)),
        'performance': int(round(performance_score)),
        'security': int(round(security_score)),
    }

