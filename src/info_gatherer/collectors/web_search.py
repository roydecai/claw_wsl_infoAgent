"""多源网络搜索收集器

支持多个搜索源：
- Jina AI (r.jina.ai) - 免费但可能有限制
- DuckDuckGo Lite - 免登录
- SearXNG 实例 - 可自托管
- Tavily API - 需要 API Key
"""

import json
import structlog
from typing import Callable

import aiohttp

from ..models import InfoItem, SourceType
from ..config import get_settings
from .base import BaseCollector

logger = structlog.get_logger(__name__)


class SearchSource:
    """搜索源定义"""
    
    def __init__(
        self,
        name: str,
        search_func: Callable,
        priority: int = 0,
        enabled: bool = True
    ):
        self.name = name
        self.search_func = search_func
        self.priority = priority
        self.enabled = enabled


class WebSearchCollector(BaseCollector):
    """多源网络搜索收集器"""
    
    def __init__(self):
        super().__init__(SourceType.WEB_SEARCH)
        self.settings = get_settings()
        
        # 初始化搜索源 - 按优先级排序 (数值越小优先级越高)
        self.sources: list[SearchSource] = [
            SearchSource("tavily", self._search_tavily, priority=1, enabled=bool(self.settings.tavily_api_key)),
            SearchSource("jina_ai", self._search_jina_ai, priority=2, enabled=True),
            SearchSource("duckduckgo", self._search_duckduckgo, priority=3, enabled=True),
        ]
    
    async def collect(self, query: str, max_results: int = 10) -> list[InfoItem]:
        """
        执行网络搜索，按优先级尝试多个搜索源
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            信息项列表
        """
        self._logger.info("starting_web_search", query=query, max_results=max_results)
        
        items = []
        errors = []
        
        # 按优先级排序搜索源
        sorted_sources = sorted(
            [s for s in self.sources if s.enabled],
            key=lambda s: s.priority
        )
        
        for source in sorted_sources:
            try:
                self._logger.info("trying_search_source", source=source.name)
                items = await source.search_func(query, max_results)
                
                if items:
                    self._logger.info("search_source_succeeded", 
                                    source=source.name, 
                                    items_found=len(items))
                    break
                    
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")
                self._logger.warning("search_source_failed", 
                                   source=source.name, 
                                   error=str(e))
                continue
        
        if not items and errors:
            self._logger.error("all_search_sources_failed", errors=errors)
        
        self._logger.info("web_search_completed", 
                        items_found=len(items),
                        sources_tried=len(sorted_sources))
        return items
    
    async def _search_jina_ai(self, query: str, max_results: int) -> list[InfoItem]:
        """使用 Jina AI 搜索"""
        search_url = f"https://r.jina.ai/search?q={query}&num={max_results}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                search_url, 
                timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            ) as response:
                if response.status == 200:
                    data = await response.text()
                    return self._parse_jina_results(data)
                elif response.status == 403:
                    raise Exception("Jina AI returned 403 Forbidden - rate limited or blocked")
                else:
                    raise Exception(f"Jina AI returned {response.status}")
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> list[InfoItem]:
        """使用 DuckDuckGo Lite 搜索"""
        # DuckDuckGo Lite HTML 端点
        search_url = "https://lite.duckduckgo.com/lite/"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                search_url,
                data={"q": query, "kl": "wt-wt"},
                timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html",
                }
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_duckduckgo_html(html, max_results)
                else:
                    raise Exception(f"DuckDuckGo returned {response.status}")
    
    async def _search_tavily(self, query: str, max_results: int) -> list[InfoItem]:
        """使用 Tavily API 搜索（需要 API Key）"""
        api_key = self.settings.tavily_api_key
        if not api_key:
            raise Exception("tavily_api_key not set in settings")
        
        url = "https://api.tavily.com/search"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
                timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_tavily_results(data)
                else:
                    raise Exception(f"Tavily returned {response.status}")
    
    def _parse_jina_results(self, raw_data: str) -> list[InfoItem]:
        """解析 Jina AI 搜索结果"""
        items = []
        
        try:
            # Jina AI 返回 JSONLines 格式
            for line in raw_data.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    result = json.loads(line)
                    item = InfoItem(
                        id=self._generate_id(result.get('url', ''), result.get('title', '')),
                        title=result.get('title', ''),
                        url=result.get('url'),
                        source=result.get('site', 'Jina AI'),
                        source_type=self.source_type,
                        content=result.get('content', '')[:500],
                        summary=result.get('description'),
                        relevance_score=result.get('score', 0.5),
                    )
                    if item.title:  # 只添加有标题的结果
                        items.append(item)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self._logger.error("parse_jina_failed", error=str(e))
        
        return items
    
    def _parse_duckduckgo_html(self, html: str, max_results: int) -> list[InfoItem]:
        """解析 DuckDuckGo Lite HTML 结果"""
        from bs4 import BeautifulSoup
        
        items = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # DuckDuckGo Lite 结果在 .result-link 中
            results = soup.select('.result-link')[:max_results]
            
            for i, result in enumerate(results):
                link = result.get('href', '')
                # 提取标题（在相邻的 .result-title 中）
                title_elem = result.find_previous(class_='result-title')
                title = title_elem.get_text(strip=True) if title_elem else f"Result {i+1}"
                
                # 提取摘要（在相邻的 .result-snippet 中）
                snippet_elem = result.find_previous(class_='result-snippet')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if link and title:
                    item = InfoItem(
                        id=self._generate_id(link, title),
                        title=title,
                        url=link,
                        source="DuckDuckGo",
                        source_type=self.source_type,
                        content=snippet[:500],
                        summary=snippet[:200] if snippet else None,
                        relevance_score=0.5,
                    )
                    items.append(item)
                    
        except Exception as e:
            self._logger.error("parse_duckduckgo_failed", error=str(e))
        
        return items
    
    def _parse_tavily_results(self, data: dict) -> list[InfoItem]:
        """解析 Tavily API 结果"""
        items = []
        
        try:
            results = data.get("results", [])
            
            for result in results:
                item = InfoItem(
                    id=self._generate_id(result.get('url', ''), result.get('title', '')),
                    title=result.get('title', ''),
                    url=result.get('url'),
                    source=result.get('source', 'Tavily'),
                    source_type=self.source_type,
                    content=result.get('content', '')[:500],
                    summary=result.get('content', '')[:200],
                    relevance_score=result.get('score', 0.5),
                )
                if item.title:
                    items.append(item)
                    
        except Exception as e:
            self._logger.error("parse_tavily_failed", error=str(e))
        
        return items
