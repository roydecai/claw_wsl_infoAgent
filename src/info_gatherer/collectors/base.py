"""收集器基类"""

from abc import ABC, abstractmethod
from typing import Optional
import structlog

from ..models import InfoItem, SourceType

logger = structlog.get_logger(__name__)


class BaseCollector(ABC):
    """信息收集器抽象基类"""
    
    def __init__(self, source_type: SourceType):
        self.source_type = source_type
        self._logger = logger.bind(collector=source_type.value)
    
    @abstractmethod
    async def collect(self, query: str, max_results: int = 10) -> list[InfoItem]:
        """
        执行信息收集
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            信息项列表
        """
        pass
    
    async def validate_result(self, item: InfoItem) -> bool:
        """
        验证结果有效性
        
        Args:
            item: 信息项
            
        Returns:
            是否有效
        """
        # 基本验证：标题不为空
        if not item.title or not item.title.strip():
            return False
        return True
    
    def _generate_id(self, url: str, title: str) -> str:
        """生成唯一ID"""
        import hashlib
        content = f"{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
