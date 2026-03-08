#!/bin/bash
# infoAgent 每日报告生成脚本 - 支持飞书文档输出

# 设置环境变量
export INFO_GATHERER_TAVILY_API_KEY="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"
export INFO_GATHERER_LLM_API_KEY="sk-sp-184218fb270448959824dcf00a1a2451"
export INFO_GATHERER_LLM_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
export INFO_GATHERER_LLM_MODEL="glm-5"
export INFO_GATHERER_LLM_MAX_TOKENS=10000
export INFO_GATHERER_LLM_TEMPERATURE=0.3
export INFO_GATHERER_LLM_TIMEOUT_SECONDS=30

# 进入项目目录
cd /home/wenweicai/.openclaw/workspace/info_gatherer

# 激活虚拟环境
source .venv/bin/activate

# 生成新版报告（按主题分类、带超链接）
python3 scripts/feishu_report_v2.py

echo ""
echo "📄 飞书文档报告: https://feishu.cn/docx/P13IdtCyvojTcfxgVmVcakaun3f"
echo "💡 请检查飞书文档内容，如需修改请手动编辑"
