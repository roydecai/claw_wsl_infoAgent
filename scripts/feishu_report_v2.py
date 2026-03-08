#!/usr/bin/env python3
"""
飞书文档报告生成脚本 - 按主题分类、带超链接
"""
import os
import sys
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/wenweicai/.openclaw/workspace/info_gatherer/src')

from info_gatherer import InfoGathererAgent
from info_gatherer.models import GatherRequest, SourceType

# 按主题分类的映射
TOPIC_CATEGORIES = {
    '前沿科技': ['科创', '科技', '激光', '质子', '算法', '黑洞', '引力波', '水凝胶'],
    '互联网科技': ['网易', 'OpenAI', 'AI', '比亚迪', '电池', '互联网', '热榜'],
    '综合新闻': ['新华网', 'BBC', '纽约时报', 'Google', '百度', '新闻'],
}

def categorize_item(item):
    """根据标题和内容分类"""
    title = item.title.lower() if item.title else ''
    content = item.content.lower() if item.content else ''
    text = title + ' ' + content
    
    for category, keywords in TOPIC_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return category
    return '其他'

async def generate_feishu_report():
    """生成飞书文档格式的报告"""
    
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
        
        # 按主题分类
        categorized = {}
        for item in result.items:
            category = categorize_item(item)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)
        
        # 生成Markdown格式报告（飞书文档格式）
        md_content = f"""# infoAgent {report_type} - {date_str} {time_str}

## 信息概览

**查询主题**: {query}  
**收集时间**: {date_str} {time_str}  
**结果数量**: 共找到 **{len(result.items)} 条**相关信息  
**收集耗时**: {result.duration_seconds:.2f} 秒

---

## 按主题分类

"""
        
        # 按分类顺序输出
        category_order = ['前沿科技', '互联网科技', '综合新闻', '其他']
        
        for category in category_order:
            if category not in categorized:
                continue
                
            items = categorized[category]
            md_content += f"### {'🔬' if category == '前沿科技' else '📱' if category == '互联网科技' else '📰' if category == '综合新闻' else '📄'} {category}\n\n"
            
            for item in items:
                # 标题加超链接
                if item.url:
                    md_content += f"#### [{item.title}]({item.url})\n"
                else:
                    md_content += f"#### {item.title}\n"
                
                md_content += f"**来源**: {item.source}  \n"
                md_content += f"**相关度**: {'⭐' * int(item.relevance_score * 5)} ({item.relevance_score:.2f})\n\n"
                
                if item.summary:
                    md_content += f"**摘要**: {item.summary}\n"
                
                md_content += "\n---\n\n"
        
        md_content += f"""## 统计信息

| 指标 | 数值 |
|------|------|
| 原始条目 | {result.total_count} |
| 去重数量 | {result.dedup_count} |
| 采集错误 | {result.error_count} |
| 数据来源 | Tavily API |

---

*报告生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')} CST*  
*生成工具: infoAgent Subagent*
"""
        
        # 输出到本地文件
        local_file = f"/home/wenweicai/.openclaw/workspace/info_gatherer/reports/{date_str}_{report_type}.md"
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        with open(local_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ 本地报告已保存: {local_file}")
        print(f"📄 飞书文档URL: https://feishu.cn/docx/P13IdtCyvojTcfxgVmVcakaun3f")
        print(f"💡 请将上述内容复制到飞书文档中")
        
        return md_content
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(generate_feishu_report())
