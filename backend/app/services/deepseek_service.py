from typing import Optional
import requests
from flask import current_app, has_app_context
import re
import html
import logging
import os


class DeepSeekClient:
    """DeepSeek API 适配器：提供SQL分析和重写功能"""

    def __init__(self):
        self.base_url = None
        self.api_key = None
        self.model = None
        self.timeout = 120
        self.enabled = True
        self._load_config()

    def _load_config(self):
        try:
            if has_app_context():
                # 优先使用Flask配置
                cfg = current_app.config
                self.base_url = cfg.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
                self.api_key = cfg.get("DEEPSEEK_API_KEY")
                self.model = cfg.get("DEEPSEEK_MODEL", "deepseek-reasoner")
                self.timeout = cfg.get("DEEPSEEK_TIMEOUT", 300)
                self.enabled = cfg.get("LLM_ENABLED", True)
            else:
                # 兜底使用环境变量
                self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
                self.api_key = os.getenv("DEEPSEEK_API_KEY")
                self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
                self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "300"))
                self.enabled = os.getenv("LLM_ENABLED", "true").lower() != "false"
        except Exception as e:
            # 配置加载失败时的兜底处理
            import logging
            logging.warning(f"DeepSeek配置加载失败，使用默认值: {e}")
            self.base_url = "https://api.deepseek.com"
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.model = "deepseek-reasoner"
            self.timeout = 300
            self.enabled = True

    def _build_prompt(self, sql: str, meta_summary: str) -> str:
        """构造系统提示。仅支持 MySQL，直接返回分析内容。
        meta_summary: 后端提炼的表/索引/执行计划摘要（可为空字符串）。
        """
        return (
            "你是资深MySQL查询优化专家。根据给定SQL与元数据/执行计划摘要，提供优化分析。\n"
            "重要原则：\n"
            "1) 只有在明确存在性能问题或可显著提升效率时才建议优化\n"
            "2) 不要为了优化而优化，简单的管理查询通常不需要改动\n"
            "3) 不要改变查询的业务语义（如随意添加LIMIT、WHERE等）\n"
            "4) 优先考虑索引建议而非SQL改写\n\n"
            "请直接输出分析内容，无需JSON格式。\n"
            f"\n【SQL】:\n{sql}\n"
            f"\n【摘要】:\n{meta_summary}\n"
        )

    def _build_analyze_prompt(self, sql: str, context_summary: str = "") -> str:
        """
        构建SQL分析的提示词
        """
        context_part = f"\n\n上下文：{context_summary}" if context_summary else ""
        
        return f"""SQL: {sql}{context_part}

性能分析（200字内）："""


    def _make_api_call(self, messages, max_tokens=1200, max_retries=2):
        """统一的API调用方法"""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }

        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                
                # 获取响应内容
                message = data.get("choices", [{}])[0].get("message", {})
                
                # 只返回最终内容，不包含思考过程
                content = message.get('content', '')
                    
                return content.strip()
                
            except Exception as e:
                if attempt < max_retries:
                    logging.warning(f"DeepSeek API call attempt {attempt + 1} failed: {str(e)}, retrying...")
                    continue
                else:
                    logging.error(f"DeepSeek API call failed after {max_retries + 1} attempts: {str(e)}")
                    raise
        
        return None

    def rewrite_sql(self, sql: str, meta_summary: str = "") -> Optional[str]:
        """返回分析内容；若出错，返回 None。"""
        if not self.enabled or not self.api_key:
            return None

        try:
            prompt = self._build_prompt(sql, meta_summary)
            messages = [
                {"role": "system", "content": "你是一个MySQL查询优化专家。"},
                {"role": "user", "content": prompt},
            ]
            
            content = self._make_api_call(messages, max_tokens=800)
            if not content:
                return None
            
            # 统一做 Markdown 符号清洗，保留文本内容
            return strip_markdown(content).strip()
            
        except Exception as e:
            logging.error(f"DeepSeek rewrite_sql error: {str(e)}")
            return None

    def analyze_sql(self, sql: str, context_summary: str = "") -> Optional[dict]:
        """
        分析SQL语句
        """
        try:
            if not self.enabled:
                return None
                
            if not self.api_key:
                logging.error("DeepSeek API key not configured")
                return None
            
            # 构建提示和消息
            prompt = self._build_analyze_prompt(sql, context_summary)
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 调用API
            response = self._make_api_call(messages)
            if not response:
                return None
            
            # 直接处理响应内容
            content = response.strip()
            
            # 统一做 Markdown 符号清洗，保留文本内容
            analysis_text = strip_markdown(content).strip()
            
            return {
                "analysis": analysis_text if analysis_text else None,
                "rewritten_sql": None
            }
            
        except Exception as e:
            logging.error(f"Error analyzing SQL: {str(e)}")
            return None


# 全局工厂方法
def get_deepseek_client() -> DeepSeekClient:
    return DeepSeekClient()


# 统一 Markdown 清洗函数
def strip_markdown(text: str) -> str:
    if not text:
        return ""
    s = text.replace("\r\n", "\n")

    # 1) 代码块（```lang\n...\n``` 或 ~~~），去围栏保留内容
    s = re.sub(r"```[\w+-]*\n?", "", s)
    s = s.replace("```", "")
    s = re.sub(r"~~~[\w+-]*\n?", "", s)
    s = s.replace("~~~", "")

    # 2) 行内代码 `code`
    s = s.replace("`", "")

    # 3) 链接/图片 [text](url) / ![alt](url) -> 仅保留可读文字
    s = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", s)

    # 4) 标题/引用/列表/有序列表/分割线
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s{0,3}>\s?", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s{0,3}(-|\*|\+)\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s{0,3}\d+[.)]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s{0,3}([-*_]\s*){3,}\s*$", "", s, flags=re.MULTILINE)

    # 5) 粗体/斜体（去掉标记保留正文）
    s = s.replace("**", "").replace("__", "")
    s = s.replace("*", "").replace("_", "")

    # 6) 内联 HTML 与实体
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)

    # 7) 多余空白
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()