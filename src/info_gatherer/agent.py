"""综合信息收集 Agent"""

from __future__ import annotations

import asyncio
import time

import structlog

from .collectors import LocalSearchCollector, WebFetchCollector, WebSearchCollector
from .config import get_settings
from .models import GatherRequest, GatherResult, InfoItem, SourceType
from .processors import DedupProcessor, RankProcessor, SummarizeProcessor
from .utils import CacheManager

logger = structlog.get_logger(__name__)


class InfoGathererAgent:
    """综合信息收集 Agent。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache_manager = CacheManager()

        # 初始化收集器
        self.collectors = {
            SourceType.WEB_SEARCH: WebSearchCollector(),
            SourceType.WEB_FETCH: WebFetchCollector(),
            SourceType.LOCAL_FILE: LocalSearchCollector(),
        }

        # 初始化处理器
        self.dedup_processor = DedupProcessor()
        self.rank_processor = RankProcessor()
        self.summarize_processor = SummarizeProcessor(
            max_summary_length=self.settings.max_summary_length,
        )

        logger.info("agent_initialized")

    def add_local_search_path(self, path: str) -> None:
        """添加本地搜索路径。"""
        collector = self.collectors.get(SourceType.LOCAL_FILE)
        if collector:
            collector.add_search_path(path)

    async def gather(self, request: GatherRequest) -> GatherResult:
        """执行信息收集任务。"""
        start_time = time.time()
        result = GatherResult(request=request)

        logger.info("gather_started", query=request.query, sources=request.sources)

        cache_key = self._build_cache_key(request)
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.info("gather_cache_hit", query=request.query)
            return GatherResult.model_validate(cached_result)

        # 步骤1：并行收集信息
        all_items, collect_error_count = await self._collect(request)
        result.total_count = len(all_items)
        result.error_count = collect_error_count

        # 步骤2：去重
        unique_items, dedup_count = self.dedup_processor.process(all_items)
        result.dedup_count = dedup_count

        # 步骤3：计算相关度并排序
        for item in unique_items:
            item.relevance_score = self.rank_processor.compute_relevance_score(item, request.query)
        sorted_items = self.rank_processor.process(unique_items, "relevance")

        # 步骤4：生成摘要
        final_items = self.summarize_processor.process(sorted_items)

        # 限制结果数量
        result.items = final_items[: request.max_results]
        result.duration_seconds = time.time() - start_time

        self.cache_manager.set(cache_key, result.model_dump(mode="json"))

        logger.info(
            "gather_completed",
            total=result.total_count,
            unique=len(result.items),
            dedup=result.dedup_count,
            errors=result.error_count,
            duration=result.duration_seconds,
        )

        return result

    async def _collect(self, request: GatherRequest) -> tuple[list[InfoItem], int]:
        """并行收集信息。"""
        all_items: list[InfoItem] = []
        error_count = 0
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_requests)

        async def _run_collector(source_type: SourceType) -> list[InfoItem]:
            collector = self.collectors.get(source_type)
            if not collector:
                logger.warning("collector_not_found", source_type=source_type)
                return []
            async with semaphore:
                return await collector.collect(request.query, request.max_results)

        tasks = [_run_collector(source_type) for source_type in request.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for collector_result in results:
            if isinstance(collector_result, list):
                all_items.extend(collector_result)
            elif isinstance(collector_result, Exception):
                error_count += 1
                logger.error("collector_failed", error=str(collector_result))

        return all_items, error_count

    def generate_report(self, result: GatherResult, format: str = "markdown") -> str:
        """生成报告。"""
        if format == "markdown":
            return self._generate_markdown_report(result)
        if format == "json":
            return result.model_dump_json(indent=2)
        return self._generate_text_report(result)

    def _generate_markdown_report(self, result: GatherResult) -> str:
        """生成 Markdown 报告。"""
        query = result.request.query
        overview = self.summarize_processor.generate_overview(result.items, query)

        report = "# 信息收集报告\n\n"
        report += f"{overview}\n\n"
        report += f"**收集耗时**: {result.duration_seconds:.2f} 秒\n"
        report += f"**原始条目**: {result.total_count}\n"
        report += f"**去重数量**: {result.dedup_count}\n"
        report += f"**采集错误**: {result.error_count}\n\n"
        report += "## 详细信息\n\n"

        for i, item in enumerate(result.items, 1):
            report += f"### {i}. {item.title}\n\n"
            if item.url:
                report += f"**来源**: [{item.source}]({item.url})\n"
            else:
                report += f"**来源**: {item.source}\n"

            report += f"**相关度**: {item.relevance_score:.2f}\n"

            if item.summary:
                report += f"\n**摘要**: {item.summary}\n"

            if item.tags:
                report += f"\n**标签**: {', '.join(item.tags)}\n"

            report += "\n---\n\n"

        return report

    def _generate_text_report(self, result: GatherResult) -> str:
        """生成纯文本报告。"""
        query = result.request.query

        report = "=== 信息收集报告 ===\n"
        report += f"查询: {query}\n"
        report += f"找到 {len(result.items)} 条结果（原始 {result.total_count}，去重 {result.dedup_count}）\n\n"

        for i, item in enumerate(result.items, 1):
            report += f"[{i}] {item.title}\n"
            if item.url:
                report += f"    来源: {item.url}\n"
            if item.summary:
                summary = item.summary[:100] + "..." if len(item.summary) > 100 else item.summary
                report += f"    摘要: {summary}\n"
            report += "\n"

        return report

    @staticmethod
    def _build_cache_key(request: GatherRequest) -> str:
        sources = ",".join(sorted(source.value for source in request.sources))
        return f"query:{request.query}|max:{request.max_results}|sources:{sources}|time:{request.time_range}"
