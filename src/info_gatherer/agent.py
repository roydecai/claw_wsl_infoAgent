"""综合信息收集 Agent"""

import asyncio
import time
from typing import Optional
import structlog

from .models import GatherRequest, GatherResult, InfoItem, SourceType
from .collectors import WebSearchCollector, WebFetchCollector, LocalSearchCollector
from .processors import DedupProcessor, RankProcessor, SummarizeProcessor
from .config import get_settings

logger = structlog.get_logger(__name__)


class InfoGathererAgent:
    """综合信息收集 Agent"""
    
    def __init__(self):
        """初始化 Agent"""
        self.settings = get_settings()
        
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
            max_summary_length=self.settings.max_summary_length
        )
        
        logger.info("agent_initialized")
    
    def add_local_search_path(self, path: str) -> None:
        """添加本地搜索路径"""
        collector = self.collectors.get(SourceType.LOCAL_FILE)
        if collector:
            collector.add_search_path(path)
    
    async def gather(self, request: GatherRequest) -> GatherResult:
        """
        执行信息收集任务
        
        Args:
            request: 收集请求
            
        Returns:
            收集结果
        """
        start_time = time.time()
        result = GatherResult(request=request)
        
        logger.info("gather_started", query=request.query, sources=request.sources)
        
        # 步骤1：并行收集信息
        all_items = await self._collect(request)
        
        # 步骤2：去重
        unique_items, dedup_count = self.dedup_processor.process(all_items)
        result.dedup_count = dedup_count
        
        # 步骤3：计算相关度并排序
        for item in unique_items:
            item.relevance_score = self.rank_processor.compute_relevance_score(
                item, request.query
            )
        sorted_items = self.rank_processor.process(unique_items, "relevance")
        
        # 步骤4：生成摘要
        final_items = self.summarize_processor.process(sorted_items)
        
        # 限制结果数量
        final_items = final_items[:request.max_results]
        
        # 设置结果
        result.items = final_items
        result.duration_seconds = time.time() - start_time
        
        logger.info("gather_completed", 
                   total=result.total_count,
                   unique=len(final_items),
                   duration=result.duration_seconds)
        
        return result
    
    async def _collect(self, request: GatherRequest) -> list[InfoItem]:
        """并行收集信息"""
        all_items = []
        
        # 并行执行所有收集器
        tasks = []
        for source_type in request.sources:
            collector = self.collectors.get(source_type)
            if collector:
                task = collector.collect(request.query, request.max_results)
                tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        for items in results:
            if isinstance(items, list):
                all_items.extend(items)
            elif isinstance(items, Exception):
                logger.error("collector_failed", error=str(items))
                result.error_count += 1
        
        return all_items
    
    def generate_report(self, result: GatherResult, format: str = "markdown") -> str:
        """
        生成报告
        
        Args:
            result: 收集结果
            format: 输出格式 ('markdown', 'json', 'text')
            
        Returns:
            报告文本
        """
        if format == "markdown":
            return self._generate_markdown_report(result)
        elif format == "json":
            return result.model_dump_json(indent=2)
        else:
            return self._generate_text_report(result)
    
    def _generate_markdown_report(self, result: GatherResult) -> str:
        """生成 Markdown 报告"""
        query = result.request.query
        
        # 生成概览
        overview = self.summarize_processor.generate_overview(result.items, query)
        
        # 构建报告
        report = f"# 信息收集报告\n\n"
        report += f"{overview}\n\n"
        report += f"**收集耗时**: {result.duration_seconds:.2f} 秒\n"
        report += f"**去重数量**: {result.dedup_count}\n\n"
        
        # 详细信息
        report += "## 详细信息\n\n"
        
        for i, item in enumerate(result.items, 1):
            report += f"### {i}. {item.title}\n\n"
            
            if item.url:
                report += f"**来源**: [{item.source}]({item.url})\n"
            else:
                report += f"**来源**: {item.source}\n"
            
            if item.summary:
                report += f"\n**摘要**: {item.summary}\n"
            
            if item.tags:
                report += f"\n**标签**: {', '.join(item.tags)}\n"
            
            report += f"\n---\n\n"
        
        return report
    
    def _generate_text_report(self, result: GatherResult) -> str:
        """生成纯文本报告"""
        query = result.request.query
        
        report = f"=== 信息收集报告 ===\n"
        report += f"查询: {query}\n"
        report += f"找到 {len(result.items)} 条结果\n\n"
        
        for i, item in enumerate(result.items, 1):
            report += f"[{i}] {item.title}\n"
            if item.url:
                report += f"    来源: {item.url}\n"
            if item.summary:
                summary = item.summary[:100] + "..." if len(item.summary) > 100 else item.summary
                report += f"    摘要: {summary}\n"
            report += "\n"
        
        return report
