# 信息收集 Subagent - Phase 1 MVP

综合信息收集 Subagent 的最小可用版本（MVP）。

## 功能特性

- **多源信息收集**：支持网络搜索、网页抓取、本地文件搜索
- **智能去重**：基于内容指纹的去重算法
- **相关性排序**：根据查询词计算相关度分数
- **自动摘要**：生成信息摘要
- **多种输出格式**：支持 Markdown、JSON、纯文本

## 快速开始

### 安装

```bash
# 进入项目目录
cd info_gatherer

# 安装依赖
pip install -e .
```

### 使用

```bash
# 基本用法
python -m info_gatherer "Python async"

# 指定结果数量
python -m info_gatherer "AI news" -n 20

# 指定信息来源
python -m info_gatherer "技术文档" -s web_search web_fetch

# 指定本地搜索路径
python -m info_gatherer "OpenClaw" --local-path /path/to/docs

# 指定输出格式
python -m info_gatherer "教程" -o json

# 详细输出
python -m info_gatherer "教程" -v
```

## 项目结构

```
info_gatherer/
├── pyproject.toml
├── README.md
├── src/
│   └── info_gatherer/
│       ├── __init__.py
│       ├── __main__.py          # CLI入口
│       ├── agent.py             # 主Agent类
│       ├── config.py            # 配置管理
│       ├── models.py            # 数据模型
│       ├── collectors/          # 收集器模块
│       │   ├── base.py
│       │   ├── web_search.py
│       │   ├── web_fetch.py
│       │   └── local_search.py
│       ├── processors/          # 处理器模块
│       │   ├── dedup.py
│       │   ├── rank.py
│       │   └── summarize.py
│       └── utils/
│           ├── cache.py
│           └── retry.py
└── tests/
```

## 配置

通过环境变量配置：

```bash
# 并发数
export INFO_GATHERER_MAX_CONCURRENT_REQUESTS=5

# 超时时间
export INFO_GATHERER_REQUEST_TIMEOUT_SECONDS=30

# 缓存设置
export INFO_GATHERER_CACHE_ENABLED=true
export INFO_GATHERER_CACHE_TTL_SECONDS=3600

# 重试设置
export INFO_GATHERER_MAX_RETRIES=3

# 日志级别
export INFO_GATHERER_LOG_LEVEL=INFO
```

## 作为库使用

```python
import asyncio
from info_gatherer import InfoGathererAgent
from info_gatherer.models import GatherRequest, SourceType

async def main():
    agent = InfoGathererAgent()
    
    # 添加本地搜索路径（可选）
    agent.add_local_search_path("/path/to/docs")
    
    request = GatherRequest(
        query="Python async tutorial",
        max_results=10,
        sources=[SourceType.WEB_SEARCH, SourceType.WEB_FETCH]
    )
    
    result = await agent.gather(request)
    
    # 生成报告
    report = agent.generate_report(result, "markdown")
    print(report)

asyncio.run(main())
```

## 技术栈

- Python 3.10+
- aiohttp - 异步 HTTP 客户端
- pydantic - 数据验证
- structlog - 结构化日志
- beautifulsoup4 - HTML 解析

## 后续计划

- [ ] 增强数据质量（来源权重、可信度评分）
- [ ] 持续监控能力（定时任务、主题订阅）
- [ ] 接入内部知识与业务系统

---

*Phase 1 MVP - 2026-03-07*
