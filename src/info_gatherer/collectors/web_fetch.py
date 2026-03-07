"""网页抓取收集器"""

import re
from typing import Optional
from urllib.parse import urlparse
import structlog
from bs4 import BeautifulSoup

from ..models import InfoItem, SourceType
from ..config import get_settings
from .base import BaseCollector

logger = structlog.get_logger(__name__)


class WebFetchCollector(BaseCollector):
    """网页抓取收集器"""
    
    def __init__(self):
        super().__init__(SourceType.WEB_FETCH)
        self.settings = get_settings()
    
    async def collect(self, query: str, max_results: int = 10) -> list[InfoItem]:
        """
        抓取指定网页
        
        Args:
            query: URL 或搜索关键词
            max_results: 最大结果数
            
        Returns:
            信息项列表
        """
        self._logger.info("starting_web_fetch", query=query)
        
        items = []
        
        # 判断是否为 URL
        if query.startswith('http://') or query.startswith('https://'):
            urls = [query]
        else:
            # 如果是关键词，先搜索获取 URL
            urls = await self._search_for_urls(query, max_results)
        
        # 并行抓取每个 URL
        import asyncio
        tasks = [self._fetch_url(url) for url in urls[:max_results]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, InfoItem):
                items.append(result)
            elif isinstance(result, Exception):
                self._logger.error("fetch_failed", error=str(result))
        
        self._logger.info("web_fetch_completed", items_found=len(items))
        return items
    
    async def _search_for_urls(self, query: str, max_results: int) -> list[str]:
        """搜索获取 URL 列表"""
        # 使用 Jina AI 搜索获取 URL
        try:
            import aiohttp
            search_url = f"https://r.jina.ai/search?q={query}&num={max_results}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
                ) as response:
                    if response.status == 200:
                        import json
                        data = await response.text()
                        urls = []
                        for line in data.strip().split('\n'):
                            if line.strip():
                                try:
                                    result = json.loads(line)
                                    if result.get('url'):
                                        urls.append(result['url'])
                                except json.JSONDecodeError:
                                    continue
                        return urls
        except Exception as e:
            self._logger.error("url_search_failed", error=str(e))
        return []
    
    async def _fetch_url(self, url: str) -> Optional[InfoItem]:
        """抓取单个 URL"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(url, html)
        except Exception as e:
            self._logger.error("url_fetch_failed", url=url, error=str(e))
        return None
    
    def _parse_html(self, url: str, html: str) -> InfoItem:
        """解析 HTML 内容"""
        soup = BeautifulSoup(html, 'lxml')
        
        # 提取标题
        title = ""
        if soup.title:
            title = soup.title.string or ""
        elif soup.h1:
            title = soup.h1.get_text(strip=True)
        
        # 去除脚本和样式
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # 提取正文
        content = soup.get_text(separator=' ', strip=True)
        # 压缩空白
        content = re.sub(r'\s+', ' ', content)
        content = content[:2000]  # 限制长度
        
        # 提取描述
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        # 提取站点名称
        parsed = urlparse(url)
        source = parsed.netloc or "Unknown"
        
        return InfoItem(
            id=self._generate_id(url, title),
            title=title,
            url=url,
            source=source,
            source_type=self.source_type,
            content=content,
            summary=description or content[:200],
            relevance_score=0.5,
        )
