"""网络搜索收集器"""

import json
from typing import Optional
import structlog

from ..models import InfoItem, SourceType
from ..config import get_settings
from .base import BaseCollector

logger = structlog.get_logger(__name__)


class WebSearchCollector(BaseCollector):
    """网络搜索收集器"""
    
    def __init__(self):
        super().__init__(SourceType.WEB_SEARCH)
        self.settings = get_settings()
    
    async def collect(self, query: str, max_results: int = 10) -> list[InfoItem]:
        """
        执行网络搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            信息项列表
        """
        self._logger.info("starting_web_search", query=query, max_results=max_results)
        
        items = []
        
        # 尝试使用 jina.ai 进行搜索
        try:
            search_url = f"https://r.jina.ai/search?q={query}&num={max_results}"
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url, 
                    timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        items = self._parse_search_results(data, query)
        except Exception as e:
            self._logger.error("search_failed", error=str(e))
        
        self._logger.info("web_search_completed", items_found=len(items))
        return items
    
    def _parse_search_results(self, raw_data: str, query: str) -> list[InfoItem]:
        """解析搜索结果"""
        items = []
        
        try:
            # 尝试解析 JSON 格式的搜索结果
            # Jina AI 搜索返回的是 JSONLines 格式
            for line in raw_data.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    result = json.loads(line)
                    item = InfoItem(
                        id=self._generate_id(result.get('url', ''), result.get('title', '')),
                        title=result.get('title', ''),
                        url=result.get('url'),
                        source=result.get('site', ''),
                        source_type=self.source_type,
                        content=result.get('content', '')[:500],  # 限制内容长度
                        summary=result.get('description'),
                        relevance_score=result.get('score', 0.5),
                    )
                    items.append(item)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self._logger.error("parse_failed", error=str(e))
        
        return items
