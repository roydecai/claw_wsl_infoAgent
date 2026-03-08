"""多源网络搜索收集器

支持多个搜索源：
- Tavily API - 需要 API Key (优先)
- Jina AI (r.jina.ai) - 免费但可能有限制
- DuckDuckGo Lite - 免登录
- SearXNG 实例 - 可自托管
"""

import asyncio
import json
import time
from enum import Enum
from typing import Callable

import aiohttp
import structlog

from ..config import get_settings
from ..models import InfoItem, SourceType
from .base import BaseCollector

logger = structlog.get_logger(__name__)


class SearchErrorType(str, Enum):
    """搜索错误类型分类"""
    TIMEOUT = "timeout"
    NETWORK = "network"
    HTTP_403 = "http_403"
    HTTP_429 = "http_429"
    HTTP_5XX = "http_5xx"
    HTTP_4XX = "http_4xx"
    PARSE_ERROR = "parse_error"
    CONFIG_ERROR = "config_error"
    UNKNOWN = "unknown"


class SearchError:
    """搜索错误信息"""
    
    def __init__(self, error_type: SearchErrorType, message: str, status_code: int = None):
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
    
    def __str__(self):
        if self.status_code:
            return f"[{self.error_type.value}] {self.message} (status={self.status_code})"
        return f"[{self.error_type.value}] {self.message}"


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
    """多源网络搜索收集器 - 支持 Session 复用和细粒度错误处理"""
    
    def __init__(self):
        super().__init__(SourceType.WEB_SEARCH)
        self.settings = get_settings()
        self._session: aiohttp.ClientSession | None = None
        
        # 初始化搜索源 - 按优先级排序 (数值越小优先级越高)
        self.sources: list[SearchSource] = [
            SearchSource("tavily", self._search_tavily, priority=1, enabled=bool(self.settings.tavily_api_key)),
            SearchSource("jina_ai", self._search_jina_ai, priority=2, enabled=True),
            SearchSource("duckduckgo", self._search_duckduckgo, priority=3, enabled=True),
        ]
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """获取或创建复用的 ClientSession"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
        return self._session
    
    async def close(self):
        """关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _classify_error(self, exception: Exception, status_code: int = None) -> SearchError:
        """分类错误类型"""
        if isinstance(exception, asyncio.TimeoutError):
            return SearchError(SearchErrorType.TIMEOUT, str(exception))
        
        if isinstance(exception, aiohttp.ClientError):
            return SearchError(SearchErrorType.NETWORK, str(exception))
        
        if status_code:
            if status_code == 403:
                return SearchError(SearchErrorType.HTTP_403, "Rate limited or blocked", status_code)
            elif status_code == 429:
                return SearchError(SearchErrorType.HTTP_429, "Too many requests", status_code)
            elif 500 <= status_code < 600:
                return SearchError(SearchErrorType.HTTP_5XX, f"Server error", status_code)
            elif 400 <= status_code < 500:
                return SearchError(SearchErrorType.HTTP_4XX, f"Client error", status_code)
        
        if isinstance(exception, json.JSONDecodeError):
            return SearchError(SearchErrorType.PARSE_ERROR, str(exception))
        
        return SearchError(SearchErrorType.UNKNOWN, str(exception), status_code)
    
    async def collect(self, query: str, max_results: int = 10) -> list[InfoItem]:
        """
        执行网络搜索，按优先级尝试多个搜索源
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            信息项列表
        """
        start_time = time.time()
        
        # 安全检查：query 长度限制
        if len(query) > self.settings.max_query_length:
            self._logger.warning("query_too_long", 
                               query_length=len(query),
                               max_length=self.settings.max_query_length)
            query = query[:self.settings.max_query_length]
        
        # 安全检查：query 基础清洗
        query = query.strip()
        if not query:
            self._logger.warning("empty_query_after_sanitization")
            return []
        
        self._logger.info("starting_web_search", query=query[:100], max_results=max_results)
        
        items = []
        errors: list[tuple[str, SearchError]] = []
        
        # 按优先级排序搜索源
        sorted_sources = sorted(
            [s for s in self.sources if s.enabled],
            key=lambda s: s.priority
        )
        
        for source in sorted_sources:
            source_start = time.time()
            try:
                self._logger.info("trying_search_source", source=source.name)
                items = await source.search_func(query, max_results)
                latency_ms = (time.time() - source_start) * 1000
                
                if items:
                    self._logger.info("search_source_succeeded", 
                                    source=source.name, 
                                    items_found=len(items),
                                    latency_ms=round(latency_ms, 2))
                    break
                else:
                    self._logger.warning("search_source_empty",
                                       source=source.name,
                                       latency_ms=round(latency_ms, 2))
                    errors.append((source.name, SearchError(SearchErrorType.UNKNOWN, "Empty response")))
                    
            except Exception as e:
                latency_ms = (time.time() - source_start) * 1000
                search_error = self._classify_error(e)
                errors.append((source.name, search_error))
                
                self._logger.warning("search_source_failed", 
                                   source=source.name,
                                   error_type=search_error.error_type.value,
                                   error_message=search_error.message,
                                   status_code=search_error.status_code,
                                   latency_ms=round(latency_ms, 2))
                continue
        
        total_duration_ms = (time.time() - start_time) * 1000
        
        if not items and errors:
            error_summary = ", ".join([f"{name}:{err.error_type.value}" for name, err in errors])
            self._logger.error("all_search_sources_failed", 
                             errors=error_summary,
                             total_duration_ms=round(total_duration_ms, 2))
        
        self._logger.info("web_search_completed", 
                        items_found=len(items),
                        sources_tried=len(sorted_sources),
                        total_duration_ms=round(total_duration_ms, 2))
        return items
    
    async def _search_jina_ai(self, query: str, max_results: int) -> list[InfoItem]:
        """使用 Jina AI 搜索"""
        search_url = f"https://r.jina.ai/search"
        params = {"q": query, "num": max_results}
        
        async with self.session.get(search_url, params=params) as response:
            # 安全检查：响应大小限制
            if response.content_length and response.content_length > self.settings.max_response_size:
                raise SearchError(
                    SearchErrorType.UNKNOWN,
                    f"Response too large: {response.content_length} bytes"
                )
            
            if response.status == 200:
                data = await response.text()
                # 再次检查实际内容大小
                if len(data.encode('utf-8')) > self.settings.max_response_size:
                    raise SearchError(
                        SearchErrorType.UNKNOWN,
                        f"Response content too large: {len(data)} bytes"
                    )
                return self._parse_jina_results(data)
            else:
                raise Exception(f"HTTP {response.status}")
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> list[InfoItem]:
        """使用 DuckDuckGo Lite 搜索"""
        search_url = "https://lite.duckduckgo.com/lite/"
        data = {"q": query, "kl": "wt-wt"}
        
        async with self.session.post(search_url, data=data) as response:
            # 安全检查：响应大小限制
            if response.content_length and response.content_length > self.settings.max_response_size:
                raise SearchError(
                    SearchErrorType.UNKNOWN,
                    f"Response too large: {response.content_length} bytes"
                )
            
            if response.status == 200:
                html = await response.text()
                # 再次检查实际内容大小
                if len(html.encode('utf-8')) > self.settings.max_response_size:
                    raise SearchError(
                        SearchErrorType.UNKNOWN,
                        f"Response content too large: {len(html)} bytes"
                    )
                return self._parse_duckduckgo_html(html, max_results)
            else:
                raise Exception(f"HTTP {response.status}")
    
    async def _search_tavily(self, query: str, max_results: int) -> list[InfoItem]:
        """使用 Tavily API 搜索（需要 API Key）"""
        api_key = self.settings.tavily_api_key
        if not api_key:
            raise SearchError(SearchErrorType.CONFIG_ERROR, "tavily_api_key not set in settings")
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        
        async with self.session.post(url, json=payload) as response:
            # 安全检查：响应大小限制
            if response.content_length and response.content_length > self.settings.max_response_size:
                raise SearchError(
                    SearchErrorType.UNKNOWN,
                    f"Response too large: {response.content_length} bytes"
                )
            
            if response.status == 200:
                data = await response.json()
                # Tavily 返回 JSON，检查序列化后的大小
                json_str = json.dumps(data)
                if len(json_str.encode('utf-8')) > self.settings.max_response_size:
                    raise SearchError(
                        SearchErrorType.UNKNOWN,
                        f"Response content too large: {len(json_str)} bytes"
                    )
                return self._parse_tavily_results(data)
            else:
                raise Exception(f"HTTP {response.status}")
    
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
                    if item.title:
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
            results = soup.select('.result-link')[:max_results]
            
            for i, result in enumerate(results):
                link = result.get('href', '')
                title_elem = result.find_previous(class_='result-title')
                title = title_elem.get_text(strip=True) if title_elem else f"Result {i+1}"
                
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
