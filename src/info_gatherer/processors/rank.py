"""排序处理器"""

from typing import Optional
import structlog

from ..models import InfoItem

logger = structlog.get_logger(__name__)


class RankProcessor:
    """信息排序处理器"""
    
    def __init__(self):
        pass
    
    def process(self, items: list[InfoItem], sort_by: str = "relevance") -> list[InfoItem]:
        """
        对信息列表排序
        
        Args:
            items: 信息列表
            sort_by: 排序字段 ('relevance', 'credibility', 'time')
            
        Returns:
            排序后的列表
        """
        if not items:
            return []
        
        if sort_by == "relevance":
            sorted_items = sorted(
                items, 
                key=lambda x: x.relevance_score, 
                reverse=True
            )
        elif sort_by == "credibility":
            sorted_items = sorted(
                items,
                key=lambda x: x.credibility_score,
                reverse=True
            )
        elif sort_by == "time":
            sorted_items = sorted(
                items,
                key=lambda x: x.fetched_at,
                reverse=True
            )
        else:
            sorted_items = items
        
        logger.info("rank_completed", 
                   count=len(items), 
                   sort_by=sort_by)
        
        return sorted_items
    
    def compute_relevance_score(self, item: InfoItem, query: str) -> float:
        """
        计算信息与查询的相关度
        
        Args:
            item: 信息项
            query: 查询字符串
            
        Returns:
            相关度分数 [0, 1]
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # 计算标题匹配度
        title_match = 0.0
        if item.title:
            title_lower = item.title.lower()
            title_words = set(title_lower.split())
            title_match = len(query_words & title_words) / len(query_words)
        
        # 计算内容匹配度
        content_match = 0.0
        if item.content:
            content_lower = item.content.lower()
            content_words = set(content_lower.split())
            content_match = len(query_words & content_words) / len(query_words)
        
        # 综合得分：标题权重更高
        score = title_match * 0.6 + content_match * 0.4
        
        return min(score, 1.0)
