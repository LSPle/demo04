from typing import Any, Dict
import logging
import requests

DEEPSEEK_API_KEY = "sk-7e7ee707daf0430b9ed805e2672090ec"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 300
LLM_ENABLED = True

logger = logging.getLogger(__name__)


def build_prompt(summary: Dict[str, Any]) -> str:
    system = summary.get('system', {})
    mysql = summary.get('mysql', {})
    perf = summary.get('perf', {})

    # 1) 系统指标 (systemMetrics)
    cpu = system.get('cpu_usage') or 0                 # cpuUsage
    mem = system.get('memory_usage') or 0              # memoryUsage
    io = system.get('disk_io_latency_ms') or 0         # diskIOLatency(ms)

    # 2) MySQL指标 (mysqlMetrics)
    hit = mysql.get('cache_hit_rate') or 0             # bufferPoolHitRate(%)
    running = mysql.get('threads_running') or 0        # activeConnections
    slow = mysql.get('slow_query_ratio') or 0          # slowQueryRatio(%)
    avg = mysql.get('avg_response_time_ms') or 0       # avgResponseTime(ms)
    lock = mysql.get('innodb_row_lock_time_ms') or 0   # lockWaitTime(ms)
    dead = mysql.get('deadlocks') or 0                 # deadlockCount
    index_rate = mysql.get('index_usage_rate') or 0    # indexUsageRate(%)

    # 3) 性能指标 (performanceMetrics)
    qps = perf.get('qps') or 0                          # qps
    tps = perf.get('tps') or 0                          # tps
    p95 = perf.get('p95_latency_ms') or 0               # p95Latency(ms)
    redo = perf.get('redo_write_latency_ms') or 0       # redoWalLatency(ms)

    prompt = (
        "你是资深 MySQL 数据库专家，请根据以下性能与配置相关指标，给出配置层面的优化建议：\n\n"
        "## 1. 系统指标\n"
        f"- cpuUsage：{cpu}%\n"
        f"- memoryUsage：{mem}%\n"
        f"- diskIOLatency：{io}ms\n\n"
        "## 2. MySQL指标\n"
        f"- bufferPoolHitRate：{hit}%\n"
        f"- activeConnections：{running}\n"
        f"- slowQueryRatio：{slow}%\n"
        f"- avgResponseTime：{avg}ms\n"
        f"- lockWaitTime：{lock}ms\n"
        f"- deadlockCount：{dead}\n"
        f"- indexUsageRate：{index_rate}%\n\n"
        "## 3. 性能指标\n"
        f"- qps：{qps}\n"
        f"- tps：{tps}\n"
        f"- p95Latency：{p95}ms\n"
        f"- redoWalLatency：{redo}ms\n\n"
        "## 分析要求\n\n"
        "请基于以上数据提供详细的配置优化建议，要求：\n\n"
        "1. 提供具体优化方案：按优先级（高/中/低）排序 \n"
        "2. 给出具体SQL优化语句：每条建议包含可直接执行的SQL语句，要求详细，可以携带建议值 \n"
        "3. 解释原理效果：说明优化原理和预期效果 \n"
        "4. SQL与解释分行分离，有不同的缩进，便于复制 \n"
        "5. 使用文本输出（避免Markdown），控制在400字左右\n"
        "6. 表情符号要适度，突出重点即可\n"
    )
    return prompt

def get_config_advice(inst, override: Dict[str, Any] = None) -> str:
    summary = {'system': {}, 'mysql': {}, 'perf': {}, 'slowlog': {}}
    p = override.get('performance') if isinstance(override, dict) else None
    if isinstance(p, dict):
        summary['system']['cpu_usage'] = p.get('cpuUsage')
        summary['system']['memory_usage'] = p.get('memoryUsage')
        summary['system']['disk_io_latency_ms'] = p.get('diskIOLatency')
        summary['mysql']['cache_hit_rate'] = p.get('bufferPoolHitRate')
        summary['mysql']['threads_running'] = p.get('activeConnections')
        summary['mysql']['slow_query_ratio'] = p.get('slowQueryRatio')
        summary['mysql']['avg_response_time_ms'] = p.get('avgResponseTime')
        summary['mysql']['innodb_row_lock_time_ms'] = p.get('lockWaitTime')
        summary['mysql']['deadlocks'] = p.get('deadlockCount')
        summary['mysql']['index_usage_rate'] = p.get('indexUsageRate')
        summary['perf']['qps'] = p.get('qps')
        summary['perf']['tps'] = p.get('tps')
        summary['perf']['p95_latency_ms'] = p.get('p95Latency')
        summary['perf']['redo_write_latency_ms'] = p.get('redoWalLatency')

    prompt = build_prompt(summary)
    try:
        logger.info("ConfigAdvice Performance Payload: %s", p)
        logger.info("ConfigAdvice Prompt:\n%s", prompt)
    except Exception:
        pass
    if not LLM_ENABLED or not DEEPSEEK_API_KEY:
        return ""
    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=DEEPSEEK_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = (data.get("choices", [{}])[0] or {}).get("message", {}).get("content", "")
        return (content or "").strip()
    except Exception:
        return ""
