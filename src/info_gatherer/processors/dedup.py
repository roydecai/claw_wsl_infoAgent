"""去重处理器"""

import hashlib
from typing import Optional
import structlog

from ..models import InfoItem

logger = structlog.get_logger(__name__)


class DedupProcessor:
    """信息去重处理器"""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化去重处理器
        
        Args:
            similarity_threshold: 相似度阈值，超过此值视为重复
        """
        self.similarity_threshold = similarity_threshold
    
    def process(self, items: list[InfoItem]) -> tuple[list[InfoItem], int]:
        """
        对信息列表去重
        
        Args:
            items: 原始信息列表
            
        Returns:
            (去重后的列表, 被去重的数量)
        """
        if not items:
            return [], 0
        
        unique_items = []
        seen_hashes = set()
        removed_count = 0
        
        for item in items:
            # 计算内容指纹
            fingerprint = self._compute_fingerprint(item)
            
            if fingerprint in seen_hashes:
                removed_count += 1
                continue
            
            seen_hashes.add(fingerprint)
            unique_items.append(item)
        
        logger.info("dedup_completed", 
                   original=len(items), 
                   unique=len(unique_items),
                   removed=removed_count)
        
        return unique_items, removed_count
    
    def _compute_fingerprint(self, item: InfoItem) -> str:
        """计算内容指纹"""
        # 使用标题和内容前200字符生成指纹
        content = f"{item.title}:{item.content[:200]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def compute_similarity(self, item1: InfoItem, item2: InfoItem) -> float:
        """
        计算两条信息的相似度
        
        使用简单的词集合相似度
        
        Args:
            item1: 信息1
            item2: 信息2
            
        Returns:
            相似度分数 [0, 1]
        """
        words1 = set(self._tokenize(item1.content))
        words2 = set(self._tokenize(item2.content))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _tokenize(self, text: str) -> list[str]:
        """简单分词"""
        import re
        # 转小写并提取单词
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        # 过滤掉太短的词
        return [w for w in words if len(w) > 2]
