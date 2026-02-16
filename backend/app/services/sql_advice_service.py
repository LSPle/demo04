from typing import Any, Dict, List
import logging
import requests
DEEPSEEK_API_KEY = "sk-7e7ee707daf0430b9ed805e2672090ec"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 300
LLM_ENABLED = True

logger = logging.getLogger(__name__)


def _safe_str(v: Any) -> str:
    try:
        if v is None:
            return ""
        return str(v)
    except Exception:
        return ""


def build_prompt(summary):
    sql_text = _safe_str(summary.get("sql"))
    tables: List[Dict[str, Any]] = list(summary.get("tables") or [])
    explain_rows: List[Dict[str, Any]] = list(summary.get("explain") or [])

    lines: List[str] = []
    lines.append("你是一名资深的SQL优化专家，专注于数据库性能调优。")
    lines.append("我将提供一条SQL语句以及数据库的相关信息。请完成以下任务：")
    lines.append("1. 判断原SQL是否存在性能问题、语法错误、索引使用不当、冗余条件等问题")
    lines.append("2. 如果有问题，请指出具体问题，并给出优化后的正确SQL语句")
    lines.append("3. 对优化后的SQL语句进行详细解释，说明优化点和原因")
    lines.append("4. 如果原SQL没有问题，请明确提示\"没有问题\"")
    lines.append("5. 使用文本输出（避免Markdown）,不超过400字,层次分明")
    lines.append("6. 表情符号要适度，突出重点即可")
    lines.append("7. SQL与解释分行分离，有不同的缩进，便于复制")
    lines.append("以下是我提供的数据：")

    # 用户输入的SQL
    lines.append("用户输入的SQL语句")
    lines.append(sql_text)

    # 表信息
    lines.append("表信息")
    table_names = [t.get("table_name") or t.get("name") or "" for t in tables]
    lines.append(f"- 表名列表: {', '.join([_safe_str(n) for n in table_names if n])}")
    for t in tables:
        name = t.get("table_name") or t.get("name") or ""
        approx = t.get("table_rows_approx")
        lines.append(f"- 表名: {_safe_str(name)}")
        lines.append(f"- 近似行数: {_safe_str(approx)}")
    lines.append("")

    # 列信息
    lines.append("列信息")
    for t in tables:
        name = t.get("table_name") or t.get("name") or ""
        cols = list(t.get("columns") or [])
        pk = list(t.get("primary_key") or [])
        for c in cols:
            col_name = _safe_str(c.get('name'))
            col_type = _safe_str(c.get('type'))
            col_null = _safe_str(c.get('null'))
            col_key = _safe_str(c.get('key'))
            line = f"- 列名: {col_name}; 数据类型: {col_type}; 是否允许空: {col_null}; 键类型: {col_key}"
            lines.append(line)

    # 索引信息
    lines.append("索引信息")
    for t in tables:
        idxs = list(t.get("indexes") or [])
        for idx in idxs:
            lines.append(f"- 索引名: {_safe_str(idx.get('name'))}")
            lines.append(f"- 是否唯一: {('是' if bool(idx.get('unique')) else '否')}")
            cols = ", ".join([_safe_str(x) for x in list(idx.get('columns') or [])])
            lines.append(f"- 索引列: {cols}")
            lines.append(f"- 索引类型: {_safe_str(idx.get('index_type'))}")

    # 执行计划（传统）
    lines.append("执行计划（传统）")
    for r in explain_rows:
        lines.append(f"- id: {_safe_str(r.get('id'))}")
        lines.append(f"- 选择类型: {_safe_str(r.get('select_type'))}")
        lines.append(f"- 表: {_safe_str(r.get('table'))}")
        lines.append(f"- 分区: {_safe_str(r.get('partitions'))}")
        lines.append(f"- 访问类型: {_safe_str(r.get('type'))}")
        lines.append(f"- 可能使用的索引: {_safe_str(r.get('possible_keys'))}")
        lines.append(f"- 使用索引: {_safe_str(r.get('key'))}")
        lines.append(f"- 索引长度: {_safe_str(r.get('key_len'))}")
        lines.append(f"- 连接列: {_safe_str(r.get('ref'))}")
        lines.append(f"- 扫描行数: {_safe_str(r.get('rows'))}")
        lines.append(f"- 过滤率: {_safe_str(r.get('filtered'))}")
        lines.append(f"- 额外信息: {_safe_str(r.get('Extra'))}")

    prompt = "\n".join(lines)
    return prompt


def call_deepseek(messages: List[Dict[str, Any]]) -> str:
    if not LLM_ENABLED or not DEEPSEEK_API_KEY:
        return ""

    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=DEEPSEEK_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        return content.strip()
    except Exception as e:
        logger.warning(f"DeepSeek 调用失败: {e}")
        return ""


def get_sql_advice(summary: Dict[str, Any]) -> str:
    try:
        prompt = build_prompt(summary)
        messages = [{"role": "user", "content": prompt}]
        logger.info("summary: %s", summary)
        logger.info("SQL优化 Summary Keys: %s", list(summary.keys()))
        logger.info("SQL优化 Prompt:\n%s", prompt)
        return call_deepseek(messages) or ""
    except Exception as e:
        logger.error(f"生成SQL优化建议失败: {e}")
        return ""

