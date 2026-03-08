"""CLI 入口"""

import asyncio
import argparse
import sys
import structlog

from .agent import InfoGathererAgent
from .models import GatherRequest, SourceType


def setup_logging():
    """设置日志"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="综合信息收集 Subagent - Phase 1 MVP"
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="搜索查询"
    )
    
    parser.add_argument(
        "-n", "--max-results",
        type=int,
        default=10,
        help="最大结果数量 (default: 10)"
    )
    
    parser.add_argument(
        "-s", "--sources",
        nargs="+",
        default=["web_search", "web_fetch"],
        choices=["web_search", "web_fetch", "local_file"],
        help="信息来源"
    )
    
    parser.add_argument(
        "-o", "--output",
        choices=["markdown", "json", "text"],
        default="markdown",
        help="输出格式"
    )
    
    parser.add_argument(
        "--local-path",
        action="append",
        dest="local_paths",
        help="本地搜索路径 (可多次指定)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    setup_logging()
    
    # 检查查询
    if not args.query:
        print("错误: 请提供搜索查询")
        print("用法: python -m info_gatherer <query> [options]")
        sys.exit(1)
    
    # 转换源类型
    sources = []
    for s in args.sources:
        try:
            sources.append(SourceType(s))
        except ValueError:
            print(f"警告: 未知来源类型 {s}")
    
    # 创建请求
    request = GatherRequest(
        query=args.query,
        max_results=args.max_results,
        sources=sources
    )
    
    # 创建 Agent
    agent = InfoGathererAgent()
    
    try:
        # 添加本地搜索路径
        if args.local_paths:
            for path in args.local_paths:
                agent.add_local_search_path(path)
        
        # 执行收集
        print(f"正在收集关于「{args.query}」的信息...")
        result = await agent.gather(request)
        
        # 生成报告
        report = agent.generate_report(result, args.output)
        print("\n" + report)
        
        # 返回状态码
        if not result.items:
            sys.exit(1)
    finally:
        # 确保资源释放
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
