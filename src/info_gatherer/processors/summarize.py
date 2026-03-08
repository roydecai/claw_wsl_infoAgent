"""摘要处理器 - 支持LLM增强"""

import structlog
from typing import Optional

import aiohttp

from ..config import get_settings
from ..models import InfoItem

logger = structlog.get_logger(__name__)


class LLMSummaryError(Exception):
    """LLM摘要生成错误"""
    pass


class SummarizeProcessor:
    """信息摘要处理器 - 支持LLM增强"""
    
    def __init__(self, max_summary_length: int = 500, use_llm: bool = True):
        """
        初始化摘要处理器
        
        Args:
            max_summary_length: 最大摘要长度
            use_llm: 是否使用LLM增强（需要配置API Key）
        """
        self.settings = get_settings()
        self.max_summary_length = max_summary_length
        self.use_llm = use_llm and bool(self.settings.llm_api_key)
        
        if self.use_llm:
            logger.info("llm_summary_enabled", 
                       model=self.settings.llm_model,
                       base_url=self.settings.llm_base_url)
        else:
            logger.debug("llm_summary_disabled", 
                        reason="API key not configured" if not self.settings.llm_api_key else "disabled by config")
    
    async def process(self, items: list[InfoItem]) -> list[InfoItem]:
        """
        为信息列表生成摘要
        
        Args:
            items: 信息列表
            
        Returns:
            处理后的列表
        """
        llm_count = 0
        fallback_count = 0
        
        for item in items:
            if not item.summary:
                # 尝试使用LLM生成摘要
                if self.use_llm:
                    try:
                        summary = await self._generate_llm_summary(item.content, item.title)
                        if summary:
                            item.summary = summary
                            llm_count += 1
                            continue
                    except LLMSummaryError as e:
                        logger.warning("llm_summary_failed", 
                                     title=item.title[:50],
                                     error=str(e))
                
                # LLM失败或禁用时使用简单摘要
                item.summary = self._generate_simple_summary(item.content)
                fallback_count += 1
        
        logger.info("summarize_completed", 
                   count=len(items),
                   llm_count=llm_count,
                   fallback_count=fallback_count)
        return items
    
    async def _generate_llm_summary(self, content: str, title: str = "") -> Optional[str]:
        """
        使用LLM生成智能摘要
        
        Args:
            content: 原始内容
            title: 标题（可选）
            
        Returns:
            摘要文本，失败返回None
        """
        if not content:
            return None
        
        # 截断内容以适应LLM上下文
        max_content_chars = 3000
        if len(content) > max_content_chars:
            content = content[:max_content_chars] + "..."
        
        # 构建提示词
        prompt = self._build_summary_prompt(content, title)
        
        try:
            summary = await self._call_llm_api(prompt)
            return summary
        except Exception as e:
            raise LLMSummaryError(f"LLM API call failed: {e}")
    
    def _build_summary_prompt(self, content: str, title: str = "") -> str:
        """构建摘要生成提示词"""
        title_context = f"标题: {title}\n\n" if title else ""
        
        prompt = f"""请为以下内容生成一个简洁的中文摘要（不超过100字），突出核心要点：

{title_context}内容：
{content}

要求：
1. 摘要控制在100字以内
2. 使用中文
3. 突出关键信息
4. 不要包含"本文"、"文章"等字眼
5. 直接输出摘要内容，不要添加任何前缀或说明

摘要："""
        return prompt
    
    async def _call_llm_api(self, prompt: str) -> str:
        """
        调用LLM API
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的文本
        """
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.settings.llm_max_tokens,
            "temperature": self.settings.llm_temperature
        }
        
        timeout = aiohttp.ClientTimeout(total=self.settings.llm_timeout_seconds)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMSummaryError(f"API returned {response.status}: {error_text}")
                
                data = await response.json()
                
                if "choices" not in data or not data["choices"]:
                    raise LLMSummaryError("Invalid API response: no choices")
                
                content = data["choices"][0].get("message", {}).get("content", "")
                return content.strip()
    
    def _generate_simple_summary(self, content: str) -> str:
        """
        生成简单摘要（回退方案）
        
        简单实现：取内容的前 N 个字符
        
        Args:
            content: 原始内容
            
        Returns:
            摘要
        """
        if not content:
            return ""
        
        # 去除多余空白
        content = ' '.join(content.split())
        
        if len(content) <= self.max_summary_length:
            return content
        
        # 在句号或逗号处截断
        truncated = content[:self.max_summary_length]
        last_period = max(
            truncated.rfind('。'),
            truncated.rfind('.'),
            truncated.rfind('，'),
            truncated.rfind(',')
        )
        
        if last_period > self.max_summary_length // 2:
            return truncated[:last_period + 1]
        
        return truncated + "..."
    
    def generate_overview(self, items: list[InfoItem], query: str) -> str:
        """
        生成信息概览
        
        Args:
            items: 信息列表
            query: 原始查询
            
        Returns:
            概览文本
        """
        if not items:
            return "未找到相关信息"
        
        # 统计来源
        sources = {}
        for item in items:
            source = item.source or "Unknown"
            sources[source] = sources.get(source, 0) + 1
        
        # 生成概览
        overview = f"关于「{query}」的信息收集结果：\n\n"
        overview += f"共找到 {len(items)} 条相关信息，来自 {len(sources)} 个不同来源。\n\n"
        
        # 按来源分组展示
        overview += "主要来源：\n"
        for source, count in sorted(sources.items(), key=lambda x: -x[1])[:5]:
            overview += f"- {source}: {count} 条\n"
        
        return overview
