"""摘要处理器"""

from typing import Optional
import structlog

from ..models import InfoItem

logger = structlog.get_logger(__name__)


class SummarizeProcessor:
    """信息摘要处理器"""
    
    def __init__(self, max_summary_length: int = 500):
        """
        初始化摘要处理器
        
        Args:
            max_summary_length: 最大摘要长度
        """
        self.max_summary_length = max_summary_length
    
    def process(self, items: list[InfoItem]) -> list[InfoItem]:
        """
        为信息列表生成摘要
        
        Args:
            items: 信息列表
            
        Returns:
            处理后的列表
        """
        for item in items:
            if not item.summary:
                item.summary = self._generate_summary(item.content)
        
        logger.info("summarize_completed", count=len(items))
        return items
    
    def _generate_summary(self, content: str) -> str:
        """
        生成摘要
        
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
