import os
import json
from typing import Optional
import requests
from flask import current_app
import re
import logging


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
        cfg = current_app.config
        self.base_url = cfg.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.api_key = cfg.get("DEEPSEEK_API_KEY")
        self.model = cfg.get("DEEPSEEK_MODEL", "deepseek-reasoner")
        self.timeout = cfg.get("DEEPSEEK_TIMEOUT", 120)
        self.enabled = cfg.get("LLM_ENABLED", True)

    def _build_prompt(self, sql: str, meta_summary: str) -> str:
        """构造严格输出约束的系统提示。仅支持 MySQL，仅返回可优化时的重写SQL，否则返回 null。
        meta_summary: 后端提炼的表/索引/执行计划摘要（可为空字符串）。
        """
        return (
            "你是资深MySQL查询优化专家。根据给定SQL与元数据/执行计划摘要，判断是否需要优化。\n"
            "重要原则：\n"
            "1) 只有在明确存在性能问题或可显著提升效率时才建议优化\n"
            "2) 不要为了优化而优化，简单的管理查询通常不需要改动\n"
            "3) 不要改变查询的业务语义（如随意添加LIMIT、WHERE等）\n"
            "4) 优先考虑索引建议而非SQL改写\n\n"
            "若确实需要优化且有明确更优写法，输出重写后的SQL；否则返回 null。\n"
            "必须严格输出JSON：{\"rewritten_sql\": string|null}。\n"
            "要求：1) 不输出解释文字；2) 仅做语义等价的改写；3) 禁止使用厂商特性以外的语法。\n"
            f"\n【SQL】:\n{sql}\n"
            f"\n【摘要】:\n{meta_summary}\n"
        )

    def _build_analyze_prompt(self, sql: str, context_summary: str) -> str:
        """构造分析提示"""
        return (
            "你是资深MySQL SQL审核与性能优化专家。给定SQL及相关的表结构/数据样本/上下文摘要，\n"
            "请完成两件事并严格以JSON返回：\n"
            "1) analysis: 用中文给出要点化的分析，重点关注：\n"
            "   - 查询是否存在明显的性能风险（如全表扫描大表、缺少必要索引等）\n"
            "   - 是否有语法错误或潜在问题\n"
            "   - 基于表结构和数据量的合理性评估\n"
            "   - 如果是简单的管理查询且表数据量不大，说明无需优化\n"
            "2) rewritten_sql: 只有在确实存在性能问题且有明确更优写法时才提供，否则为null\n\n"
            "重要：不要为了优化而优化，要基于实际情况判断是否真的需要改进。\n"
            "必须严格输出JSON：{\"analysis\": string, \"rewritten_sql\": string|null}。\n"
            "不要输出任何额外解释文字或代码块围栏。\n"
            f"\n【SQL】:\n{sql}\n"
            f"\n【上下文摘要（表结构与数据样本等）】:\n{context_summary}\n"
        )

    def _extract_json_from_content(self, content):
        """从内容中提取有效的JSON对象"""
        if not content:
            return None
            
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
            
        # 查找第一个完整的JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
                
        # 尝试提取代码块中的JSON
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        code_matches = re.findall(code_block_pattern, content)
        
        for code_match in code_matches:
            try:
                return json.loads(code_match.strip())
            except json.JSONDecodeError:
                continue
                
        return None

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
                content = ""
                
                # 合并所有可能的内容字段
                if message.get('reasoning_content'):
                    content += message['reasoning_content'] + "\n"
                if message.get('content'):
                    content += message['content']
                    
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
        """返回重写后的 SQL；若不需要优化或出错，返回 None。"""
        if not self.enabled or not self.api_key:
            return None

        try:
            prompt = self._build_prompt(sql, meta_summary)
            messages = [
                {"role": "system", "content": "你是一个只返回JSON的优化器。"},
                {"role": "user", "content": prompt},
            ]
            
            content = self._make_api_call(messages, max_tokens=800)
            if not content:
                return None
                
            # 使用增强的JSON提取方法
            obj = self._extract_json_from_content(content)
            if not obj:
                return None
                
            rewritten = obj.get("rewritten_sql")
            if isinstance(rewritten, str) and rewritten.strip():
                return rewritten.strip()
            return None
            
        except Exception as e:
            logging.error(f"DeepSeek rewrite_sql error: {str(e)}")
            return None

    def analyze_sql(self, sql: str, context_summary: str = "") -> Optional[dict]:
        """要求模型输出 JSON：{"analysis": string, "rewritten_sql": string|null}
        若未启用或出错，返回 None。"""
        if not self.enabled or not self.api_key:
            return None

        try:
            prompt = self._build_analyze_prompt(sql, context_summary)
            messages = [
                {"role": "system", "content": "你是一个只返回JSON的审核与优化助手。"},
                {"role": "user", "content": prompt},
            ]
            
            content = self._make_api_call(messages, max_tokens=1200)
            if not content:
                return None
                
            # 使用增强的JSON提取方法
            obj = self._extract_json_from_content(content)
            if not obj:
                logging.warning(f"Failed to extract JSON from content: {content[:200]}...")
                return None
                
            analysis = obj.get("analysis")
            rewritten = obj.get("rewritten_sql")
            
            # 规范化
            if not isinstance(analysis, str):
                analysis = None
            if not (isinstance(rewritten, str) and rewritten.strip()):
                rewritten = None
            else:
                rewritten = rewritten.strip()
                
            return {"analysis": analysis, "rewritten_sql": rewritten}
            
        except Exception as e:
            logging.error(f"DeepSeek analyze_sql error: {str(e)}")
            return None


# 全局工厂方法
def get_deepseek_client() -> DeepSeekClient:
    return DeepSeekClient()