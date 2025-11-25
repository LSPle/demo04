from typing import Any, Dict
import requests
import logging

# 说明：本服务仅基于调用方（前端）提供的指标生成提示词，不主动做窗口采样
# 目的：点击“获取数据”后得到的指标直接拼接并发送给 DeepSeek，避免二次获取

# 注意：建议将密钥改为环境变量或配置项管理，避免硬编码泄露风险；LLM_ENABLED 控制是否启用调用
DEEPSEEK_API_KEY = "sk-7e7ee707daf0430b9ed805e2672090ec"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 300
LLM_ENABLED = True

logger = logging.getLogger(__name__)


def build_prompt(summary: Dict[str, Any]) -> str:
    # 输入：summary包含 system/mysql/perf/slowlog 四类指标；缺失时以0兜底
    # 输出：用于 DeepSeek 的纯文本提示词
    system = summary.get('system', {})
    mysql = summary.get('mysql', {})
    perf = summary.get('perf', {})

    # 1) 系统资源指标
    cpu = system.get('cpu_usage') or 0
    mem = system.get('memory_usage') or 0
    disk = system.get('disk_usage') or 0
    net = system.get('network_io_mbps') or 0

    # 2) 连接与事务指标
    running = mysql.get('threads_running') or 0            # activeConnections
    cur_conn = mysql.get('threads_connected') or 0         # currentConnections
    max_conn = mysql.get('max_connections') or 0           # maxConnections
    peak = mysql.get('peak_connections') or 0              # peakConnections
    trx = mysql.get('transactions_total') or 0             # transactionCount
    repl = mysql.get('replication_delay_ms') or 0          # replicationDelay(ms)

    # 3) 查询性能指标
    qps = perf.get('qps') or 0                              # qps
    avg = mysql.get('avg_response_time_ms') or 0           # avgQueryTime(ms)
    slowest = perf.get('slowest_query_ms') or 0            # slowestQuery(ms)
    slow = mysql.get('slow_query_ratio') or 0              # slowQueryRatio(%)

    # 4) 缓存与锁指标
    hit = mysql.get('cache_hit_rate') or 0                 # bufferPoolHitRate(%)
    shared_hit = mysql.get('shared_buffer_hit_rate') or 0  # sharedBufferHitRate(%)
    lock_waits = mysql.get('innodb_row_lock_waits') or 0   # lockWaits
    dead = mysql.get('deadlocks') or 0                     # deadlocks

    prompt = (
        "你是一名资深 MySQL 数据库专家，请根据以下性能指标数据进行分析并提供优化建议：\n\n"
        "## 1. 系统资源指标\n"
        f"- cpuUsage：{cpu}%\n"
        f"- memoryUsage：{mem}%\n"
        f"- diskUsage：{disk}%\n"
        f"- networkIO：{net}MB/s\n\n"
        "## 2. 连接与事务指标\n"
        f"- activeConnections：{running}\n"
        f"- currentConnections：{cur_conn}\n"
        f"- maxConnections：{max_conn}\n"
        f"- peakConnections：{peak}\n"
        f"- transactionCount：{trx}\n"
        f"- replicationDelay：{repl}ms\n\n"
        "## 3. 查询性能指标\n"
        f"- qps：{qps}\n"
        f"- avgQueryTime：{avg}ms\n"
        f"- slowestQuery：{slowest}ms\n"
        f"- slowQueryRatio：{slow}%\n\n"
        "## 4. 缓存与锁指标\n"
        f"- bufferPoolHitRate：{hit}%\n"
        f"- sharedBufferHitRate：{shared_hit}%\n"
        f"- lockWaits：{lock_waits}\n"
        f"- deadlocks：{dead}\n\n"
        "## 分析要求\n\n"
        "请基于以上数据提供详细的优化建议，要求：\n\n"
        "1. 提供具体优化方案：按优先级（高/中/低）排序建议 \n"
        "2. 给出具体SQL优化语句：每个建议必须包含可直接执行的SQL语句，要求详细，可以携带建议值 \n"
        "3. 解释原理效果：说明优化原理和预期效果 \n"
        "4. SQL与解释分行分离，有不同的缩进，便于复制 \n"
        "5. 使用文本格式（不要任何Markdown符号）输出，控制在400字左右\n"
        "6. 表情符号要适度，突出重点即可\n"
    )
    return prompt

def call_deepseek(messages, max_tokens: int = 800) -> str:
    # 统一调用 DeepSeek Chat Completions API，返回纯文本内容
    if not LLM_ENABLED or not DEEPSEEK_API_KEY:
        return ""

    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=DEEPSEEK_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        message = (data.get("choices", [{}])[0] or {}).get("message", {})
        content = message.get("content", "")
        return content.strip()
    except Exception:
        return ""


def get_architecture_advice(inst, override: Dict[str, Any] = None) -> str:
    # 行为：仅使用请求体中的指标构造 summary，不进行窗口采样或数据库查询
    # 请求体支持两种形态之一（推荐第一种）：
    # 1) 包含 performance 对象：
    #    {
    #      "performance": {
    #        "cpuUsage": 30,
    #        "memoryUsage": 60,
    #        "diskUsage": 70,
    #        "networkIO": 12.5,
    #        "qps": 120.5,
    #        "tps": 45.2,
    #        "avgQueryTime": 12,
    #        "slowQueryRatio": 1.3,
    #        "slowestQuery": 320,
    #        "activeConnections": 45,
    #        "currentConnections": 120,
    #        "maxConnections": 500,
    #        "peakConnections": 140,
    #        "transactionCount": 2400,
    #        "lockWaits": 3,
    #        "deadlocks": 0,
    #        "bufferPoolHitRate": 98.2,
    #        "replicationDelay": 0
    #      }
    #    }
    # 2) 直接传 summary 的分组（system/mysql/perf/slowlog），字段命名见 build_prompt 读取的键
    # 缺失字段将走 0/None 兜底；如果 override 为空，summary 为空，提示词仍可生成（数值为 0）
    summary = {'system': {}, 'mysql': {}, 'perf': {}, 'slowlog': {}}
    p = override.get('performance') if isinstance(override, dict) else None
    if isinstance(p, dict):
        summary['system']['cpu_usage'] = p.get('cpuUsage')
        summary['system']['memory_usage'] = p.get('memoryUsage')
        summary['system']['disk_usage'] = p.get('diskUsage')
        summary['system']['network_io_mbps'] = p.get('networkIO')
        summary['mysql']['threads_running'] = p.get('activeConnections')
        summary['mysql']['threads_connected'] = p.get('currentConnections')
        summary['mysql']['max_connections'] = p.get('maxConnections')
        summary['mysql']['peak_connections'] = p.get('peakConnections')
        summary['mysql']['transactions_total'] = p.get('transactionCount')
        summary['mysql']['replication_delay_ms'] = p.get('replicationDelay')
        summary['mysql']['innodb_row_lock_waits'] = p.get('lockWaits')
        summary['mysql']['deadlocks'] = p.get('deadlocks')
        summary['mysql']['cache_hit_rate'] = p.get('bufferPoolHitRate')
        summary['mysql']['shared_buffer_hit_rate'] = p.get('sharedBufferHitRate')
        summary['mysql']['slow_query_ratio'] = p.get('slowQueryRatio')
        summary['mysql']['avg_response_time_ms'] = p.get('avgQueryTime')
        summary['perf']['qps'] = p.get('qps')
        summary['perf']['slowest_query_ms'] = p.get('slowestQuery')
    prompt = build_prompt(summary)
    messages = [
        {"role": "user", "content": prompt},
    ]
    try:
        logger.info("架构优化: %s", p)
        logger.info("架构优化 Prompt:\n%s", prompt)
    except Exception:
        pass
    return call_deepseek(messages, max_tokens=800) or ""
