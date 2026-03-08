# infoAgent 部署文档

**部署时间**: 2026-03-08  
**版本**: Phase 1 MVP  
**状态**: ✅ 已部署

---

## 📦 部署内容

### 1. 核心功能
- ✅ 多源信息收集（Tavily/Jina/DDG）
- ✅ 智能去重
- ✅ 相关性排序
- ✅ **LLM增强摘要**（阿里云 DashScope glm-5）
- ✅ 多种输出格式（Markdown/JSON/Text）

### 2. 定时任务
- **早报**: 每天 8:30 自动生成
- **晚报**: 每天 20:30 自动生成
- **飞书文档**: https://feishu.cn/docx/P13IdtCyvojTcfxgVmVcakaun3f

---

## 🔧 部署结构

```
/home/wenweicai/.openclaw/workspace/info_gatherer/
├── scripts/
│   └── daily_report.sh      # 定时任务脚本
├── reports/                  # 生成的报告目录
│   └── YYYY-MM-DD_早报.md
│   └── YYYY-MM-DD_晚报.md
├── logs/                     # 定时任务日志
│   ├── cron_morning.log
│   └── cron_evening.log
├── .env                      # 环境变量配置（API Keys）
└── src/
    └── info_gatherer/        # 源代码
```

---

## ⚙️ 环境配置

### API Keys（已配置）
```bash
# Tavily API（搜索增强）
INFO_GATHERER_TAVILY_API_KEY=tvly-dev-48B56E...

# 阿里云 DashScope LLM（智能摘要）
INFO_GATHERER_LLM_API_KEY=sk-sp-1842...
INFO_GATHERER_LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
INFO_GATHERER_LLM_MODEL=glm-5
INFO_GATHERER_LLM_MAX_TOKENS=10000
INFO_GATHERER_LLM_TEMPERATURE=0.3
INFO_GATHERER_LLM_TIMEOUT_SECONDS=30
```

---

## ⏰ 定时任务

### Cron 配置
```cron
# 每天早上 8:30 生成早报
30 8 * * * /home/wenweicai/.openclaw/workspace/info_gatherer/scripts/daily_report.sh

# 每天晚上 8:30 生成晚报
30 20 * * * /home/wenweicai/.openclaw/workspace/info_gatherer/scripts/daily_report.sh
```

### 手动运行
```bash
# 立即生成报告
/home/wenweicai/.openclaw/workspace/info_gatherer/scripts/daily_report.sh

# 查看定时任务
crontab -l

# 查看日志
tail -f /home/wenweicai/.openclaw/workspace/info_gatherer/logs/cron_morning.log
tail -f /home/wenweicai/.openclaw/workspace/info_gatherer/logs/cron_evening.log
```

---

## 📊 测试验证

### 单元测试
```bash
cd /home/wenweicai/.openclaw/workspace/info_gatherer
source .venv/bin/activate
python -m pytest tests/ -v

# 结果: 47 passed
```

### 代码质量
```bash
python -m ruff check src tests

# 结果: All checks passed
```

### 功能测试
```bash
# CLI 测试
python -m info_gatherer "Python async" -n 5 --output markdown

# LLM 摘要测试
python -c "from info_gatherer.processors.summarize import SummarizeProcessor; ..."
# ✅ LLM 调用成功！
```

---

## 📈 监控与维护

### 日志位置
- 应用日志: 结构化日志输出
- 定时任务日志: `logs/cron_*.log`

### 报告位置
- **本地报告**: `reports/YYYY-MM-DD_早报/晚报.md`
- **飞书文档**: https://feishu.cn/docx/P13IdtCyvojTcfxgVmVcakaun3f
  - 已为您设置编辑权限
  - 每日报告需手动复制到飞书文档（自动化集成待开发）

### 飞书文档自动化（可选）
当前需要手动将本地报告复制到飞书文档。如需完全自动化，需要：
1. 申请飞书开放平台应用权限
2. 配置飞书 App ID 和 App Secret
3. 更新脚本调用飞书 API 自动写入

### 故障排查
```bash
# 检查虚拟环境
source .venv/bin/activate

# 检查配置
python -c "from info_gatherer.config import get_settings; print(get_settings())"

# 手动运行脚本
bash scripts/daily_report.sh
```

---

## 📝 报告示例

```markdown
================================
infoAgent 晚报 - 2026-03-08 20:30
================================

# 信息收集报告

关于「今日热点新闻 科技动态」的信息收集结果：

共找到 10 条相关信息，来自 1 个不同来源。

**收集耗时**: 2.22 秒
**原始条目**: 10
**去重数量**: 0
**采集错误**: 0

## 详细信息

### 1. 文章标题
**来源**: [来源名称](URL)
**相关度**: 0.85
**摘要**: LLM生成的智能中文摘要...
```

---

## 🎯 后续优化建议

1. **增强数据质量** - 添加来源权重、可信度评分
2. **主题订阅** - 支持定制化的关键词订阅
3. **内部知识接入** - 连接企业内部文档系统
4. **报告模板** - 支持自定义报告格式
5. **通知集成** - 报告生成后自动发送到飞书/邮件

---

## ✅ 部署检查清单

- [x] 代码推送到 GitHub
- [x] 环境变量配置完成
- [x] API Keys 测试通过
- [x] 定时任务配置完成
- [x] 脚本手动运行测试通过
- [x] 报告生成功能正常
- [x] LLM 摘要功能正常
- [x] 单元测试通过（47/47）
- [x] 代码质量检查通过

---

**部署完成时间**: 2026-03-08 15:30  
**下次早报**: 明天 08:30  
**下次晚报**: 今天 20:30  

🦞
