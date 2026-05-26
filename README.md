# Hermes Skills Bridge

> 让 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 一键用上 [skills.sh](https://skills.sh) 生态的 500+ AI Agent Skills

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://python.org)
[![Skills Imported](https://img.shields.io/badge/Skills%20Imported-106-green.svg)](top100.json)
[![Vercel](https://img.shields.io/badge/Deployed-Vercel-black?logo=vercel)](https://hermes-skills-bridge.vercel.app)

## 🚀 一行命令，500+ Skills

```bash
# 导入单个 skill
python3 bridge.py import anthropics/skills --skill frontend-design

# 批量导入 Top 106
python3 bridge.py batch-import top100.json

# 查看已导入
python3 bridge.py list

# 验证格式
python3 bridge.py validate
```

## 🌐 可视化浏览

浏览所有 106 个 skills，按类型、分类、热度筛选：
[https://hermes-skills-bridge.vercel.app](https://hermes-skills-bridge.vercel.app)

## 📦 已验证的 106 Skills

来自 **18+ 个高质量仓库**，覆盖 **9 大类别**，按 **5 种类型**分类：

### 类型分类（二级标签）

| 类型 | 数量 | 说明 |
|------|------|------|
| 🛠️ Tool | 58 | 工具类技能：浏览器自动化、代码审查、数据库查询 |
| 📋 Utility | 61 | 通用技能：写作辅助、学习、规划、Prompt |
| 📐 Framework | 22 | 框架类：React、LangGraph、CrewAI、Terraform |
| ☁️ Platform | 18 | 平台类：Vercel、Cloudflare、Stripe、Supabase |
| 🤖 Agent | 6 | 智能体类：自主代理、语音代理、子代理开发 |

### 主类别分布

| 类别 | 数量 | 来源 |
|------|------|------|
| 💻 Software Development | 41 | vercel-labs, anthropics, superpowers, sickn33... |
| 🎨 Creative | 19 | anthropics, vercel-labs, op7418, lijigang... |
| 🔬 Research | 14 | lijigang, elementalsouls, firecrawl... |
| 📄 Productivity | 17 | lijigang, superpowers, OthmanAdi... |
| 🛠 DevOps | 7 | vercel-labs, cloudflare, netlify, sentry... |
| 🔴 Red Teaming | 3 | trailofbits, github |
| 📊 Data Science | 3 | neon, duckdb |
| ⚙️ MLOps | 1 | langfuse |
| 📱 Social Media | 1 | alirezarezvani |

### 热门 Skills（按 Popularity Score）

| Skill | Score | 类型 | 描述 |
|-------|-------|------|------|
| [mcp-builder](https://github.com/anthropics/skills) | 0.95 | Tool/Framework | MCP服务器构建 |
| [caveman](https://github.com/JuliusBrussee/caveman) | 0.95 | Tool/Utility | 极简代码审查，63K ⭐ |
| [claude-api](https://github.com/anthropics/skills) | 0.92 | Platform/Tool | Claude API开发 |
| [react-best-practices](https://github.com/vercel-labs/agent-skills) | 0.92 | Framework/Utility | React 70条优化规则 |
| [crewai](https://github.com/sickn33/antigravity-awesome-skills) | 0.92 | Framework/Agent | CrewAI多代理框架 |

### 按来源仓库

| 仓库 | 数量 | 亮点 Skills |
|------|------|------------|
| anthropics/skills | 17 | 官方17个核心skills |
| vercel-labs/agent-skills | 7 | React, Vercel, Web设计 |
| lijigang/ljg-skills | 14 | 认知工具箱全套 |
| sickn33/antigravity-awesome-skills | 6 | LangGraph, CrewAI, Langfuse |
| obra/superpowers | 8 | 规划、审查、开发流程 |
| cloudflare/skills | 3 | AI Agent, MCP, Docs |
| alirezarezvani/claude-skills | 7 | Docker, Terraform, SEO |
| gohypergiant/agent-skills | 3 | TypeScript, Skill管理 |
| 其他 | 41 | 来自 10+ 个独立生态仓库 |

## 🔧 工作原理

Vercel 的 `npx skills` 生态和 Hermes Agent 都使用 `SKILL.md` 格式，但 frontmatter 字段略有不同：

```
Vercel 格式                    →    Hermes 格式
---
name: xxx                           name: xxx
description: xxx                    description: xxx
license: MIT                        version: 1.0.0
metadata:                           author: vercel
  author: vercel                    license: MIT
  version: "1.0.0"                  metadata:
---                                     hermes:
                                          tags: [imported, vercel]
                                          imported_from: owner/repo
                                      ---
```

Bridge 自动完成这个转换，同时：
- 验证 name ≤ 64 字符、description ≤ 1024 字符
- 复制 scripts/ 目录（如有）
- 记录导入来源和时间
- 写入 `~/.hermes/skills/<category>/<name>/`

## 📋 所有命令

```bash
# 导入单个 skill
python3 bridge.py import <owner/repo> --skill <name> [--category <cat>]

# 批量导入
python3 bridge.py batch-import <json-file>

# 列出已导入
python3 bridge.py list

# 验证格式
python3 bridge.py validate [<name>]
```

## 📊 数据导出

所有技能数据提供两种导出格式，便于集成和分析：

### JSON (top100.json)
每个 skill 包含完整字段：name, description, category, tags, popularity_score, repo, path, reason

```json
{
  "name": "mcp-builder",
  "category": "software-development",
  "tags": ["Tool", "Framework"],
  "popularity_score": 0.95,
  "description": "Build Model Context Protocol (MCP) servers for AI tool integration",
  "repo": "anthropics/skills"
}
```

### CSV (top100.csv)
便于导入 Excel/Google Sheets 或进行数据分析：
- 106 skills × 8 字段
- 支持按 tags 列筛选（Framework/Tool/Platform/Utility/Agent）
- popularity_score 0.0-1.0 用于排序和热度分析

## 🎯 自定义扩展

编辑 `top100.json` 添加你自己的 skills：

```json
{
  "skills": [
    {
      "name": "my-skill",
      "repo": "owner/repo",
      "path": "skills/my-skill",
      "category": "software-development",
      "tags": ["Tool", "Utility"],
      "popularity_score": 0.75,
      "description": "what this skill does",
      "reason": "为什么选这个skill"
    }
  ]
}
```

## 🔗 同系列项目 — AI Agent 协作开发

这三个项目均由 **Hermes Agent + 土鳖（DeepSeek）双 Agent 协作开发**，是 AI 辅助开发的最佳实践案例。欢迎 Star、Issue、PR！

| 项目 | 描述 | 技术栈 |
|------|------|--------|
| [**okr-alignment-system**](https://github.com/freshtemp-labs/okr-alignment-system) | OKR 对齐管理系统 — 树状可视化 + 级联计算 + iCloud 同步 | Swift / SwiftUI / CoreData |
| [**ai-compute-map**](https://github.com/freshtemp-labs/ai-compute-map) | 全球 AI 算力供应链地图 — 三层数据可视化 | React / TypeScript / ECharts |
| [**ba2plus-calculator**](https://github.com/freshtemp-labs/ba2plus-calculator) | BA II Plus 金融计算器 — CFA 考试就绪 | HTML / JS / Tauri |

> 💡 **为什么这些项目值得关注？**
> - 完整的 PRD + 代码文档 + 测试覆盖
> - AI Agent 编写的代码经过人工审查和迭代优化
> - 每个项目都有 good-first-issue 标签，适合新手贡献者

## 🤝 贡献

欢迎提交 PR 添加更多验证过的 skill 路径到 `top100.json`！

## 📄 License

GPL-3.0 — 与 Hermes Agent 保持一致
