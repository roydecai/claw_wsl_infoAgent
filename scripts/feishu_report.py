#!/usr/bin/env python3
"""
飞书文档报告生成脚本
"""
import os
import sys
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/wenweicai/.openclaw/workspace/info_gatherer/src')

from info_gatherer import InfoGathererAgent
from info_gatherer.models import GatherRequest, SourceType

# 飞书文档ID（每日报告模板）
FEISHU_DOC_TOKEN = "P13IdtCyvojTcfxgVmVcakaun3f"  # 文档token

async def generate_feishu_report():
    """生成飞书文档报告"""
    
    # 获取当前时间
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    # 判断早报/晚报
    if now.hour < 12:
        report_type = "早报"
        query = "今日科技新闻 AI发展"
    else:
        report_type = "晚报"
        query = "今日热点新闻 科技动态"
    
    print(f"正在生成 {report_type}...")
    
    # 创建Agent并收集信息
    agent = InfoGathererAgent()
    
    try:
        request = GatherRequest(
            query=query,
            max_results=10,
            sources=[SourceType.WEB_SEARCH]
        )
        
        result = await agent.gather(request)
        
        # 生成Markdown格式报告
        md_content = f"""# infoAgent {report_type} - {date_str} {time_str}

## 信息收集报告

关于「{query}」的信息收集结果：

共找到 **{len(result.items)} 条**相关信息，来自 **{len(set(item.source for item in result.items))} 个不同来源**。

### 统计信息
- **收集耗时**: {result.duration_seconds:.2f} 秒
- **原始条目**: {result.total_count}
- **去重数量**: {result.dedup_count}
- **采集错误**: {result.error_count}

---

## 详细信息

"""
        
        for i, item in enumerate(result.items, 1):
            md_content += f"""### {i}. {item.title}

**来源**: [{item.source}]({item.url or '#'})
**相关度**: {item.relevance_score:.2f}

**摘要**: {item.summary or '无摘要'}

---

"""
        
        md_content += f"""## 报告生成信息
- **生成时间**: {now.strftime('%Y-%m-%d %H:%M:%S')} CST
- **报告类型**: {report_type}
- **数据来源**: Tavily API
- **生成工具**: infoAgent Subagent
"""
        
        # 输出到本地文件
        local_file = f"/home/wenweicai/.openclaw/workspace/info_gatherer/reports/{date_str}_{report_type}.md"
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        with open(local_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ 本地报告已保存: {local_file}")
        
        # 这里应该调用飞书API写入文档
        # 由于飞书API需要特殊处理，暂时输出提示
        print(f"📄 飞书文档URL: https://feishu.cn/docx/{FEISHU_DOC_TOKEN}")
        print(f"💡 请将上述内容复制到飞书文档中")
        
        return md_content
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(generate_feishu_report())
