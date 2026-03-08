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

# 获取当前日期
DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H:%M")

# 根据时间判断是早报还是晚报
if [[ "$TIME" < "12:00" ]]; then
    REPORT_TYPE="早报"
    QUERY="今日科技新闻 AI发展"
else
    REPORT_TYPE="晚报"
    QUERY="今日热点新闻 科技动态"
fi

# 生成报告（本地文件）
OUTPUT_FILE="/home/wenweicai/.openclaw/workspace/info_gatherer/reports/${DATE}_${REPORT_TYPE}.md"

# 确保报告目录存在
mkdir -p /home/wenweicai/.openclaw/workspace/info_gatherer/reports

echo "================================" >> "$OUTPUT_FILE"
echo "infoAgent ${REPORT_TYPE} - ${DATE} ${TIME}" >> "$OUTPUT_FILE"
echo "================================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 执行信息收集
python -m info_gatherer "$QUERY" -n 10 --output markdown >> "$OUTPUT_FILE" 2>&1

echo "" >> "$OUTPUT_FILE"
echo "================================" >> "$OUTPUT_FILE"
echo "报告生成时间: $(date)" >> "$OUTPUT_FILE"
echo "================================" >> "$OUTPUT_FILE"

echo "${REPORT_TYPE}已生成: $OUTPUT_FILE"

# 输出飞书文档提示
echo ""
echo "📄 飞书文档报告: https://feishu.cn/docx/P13IdtCyvojTcfxgVmVcakaun3f"
echo "💡 请手动将报告内容复制到飞书文档中（自动化集成待开发）"
