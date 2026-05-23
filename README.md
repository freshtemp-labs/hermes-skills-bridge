# Hermes Skills Bridge

> 让 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 一键用上 [skills.sh](https://skills.sh) 生态的 500+ AI Agent Skills

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://python.org)
[![Skills Imported](https://img.shields.io/badge/Skills%20Imported-55-green.svg)](top55.json)

## 🚀 一行命令，500+ Skills

```bash
# 导入单个 skill
python3 bridge.py import anthropics/skills --skill frontend-design

# 批量导入 Top 55
python3 bridge.py batch-import top55.json

# 查看已导入
python3 bridge.py list

# 验证格式
python3 bridge.py validate
```

## 📦 已验证的 Top 55 Skills

来自 **15 个高质量仓库**，覆盖 **5 大类别**：

| 类别 | 数量 | 来源 |
|------|------|------|
| 🎨 Creative | 14 | anthropics, vercel-labs, op7418, blader, JuliusBrussee... |
| 💻 Software Development | 16 | vercel-labs, anthropics, addyosmani, wondelai, SawyerHood... |
| 🔬 Research | 10 | lijigang, elementalsouls |
| 📄 Productivity | 9 | lijigang, OthmanAdi, nidhinjs, zarazhangrui... |
| 🛠 DevOps | 3 | vercel-labs, addyosmani |

### 热门 Skills

| Skill | Stars | 描述 |
|-------|-------|------|
| [caveman](https://github.com/JuliusBrussee/caveman) | ⭐ 63K | 极简代码审查 |
| [planning-with-files](https://github.com/OthmanAdi/planning-with-files) | ⭐ 21K | Manus风格持久化规划 |
| [humanizer](https://github.com/blader/humanizer) | ⭐ 20K | 去除AI写作痕迹 |
| [Humanizer-zh](https://github.com/op7418/Humanizer-zh) | ⭐ 8K | Humanizer中文版 |
| [prompt-master](https://github.com/nidhinjs/prompt-master) | ⭐ 8K | 精准Prompt生成 |
| [dev-browser](https://github.com/SawyerHood/dev-browser) | ⭐ 6K | 浏览器自动化 |
| [ljg-skills](https://github.com/lijigang/ljg-skills) | ⭐ 5.2K | 李继刚全套认知工具箱 (21个skill) |
| [react-best-practices](https://github.com/vercel-labs/agent-skills) | — | Vercel官方React性能优化70条 |
| [frontend-design](https://github.com/anthropics/skills) | — | Anthropic官方前端设计指南 |
| [osint-methodology](https://github.com/elementalsouls/Claude-OSINT) | ⭐ 1.3K | OSINT调研方法论 |

| [context-engineering](https://github.com/addyosmani/agent-skills) | ⭐ 45K | agent上下文工程指南 |
| [ci-cd-and-automation](https://github.com/addyosmani/agent-skills) | ⭐ 45K | CI/CD自动化流水线 |
| [browser-testing-with-devtools](https://github.com/addyosmani/agent-skills) | ⭐ 45K | 浏览器DevTools自动化测试 |
| [domain-driven-design](https://github.com/wondelai/skills) | ⭐ 1.1K | DDD领域驱动设计 |
| [clean-code](https://github.com/wondelai/skills) | ⭐ 1.1K | 整洁代码规范 |

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

## 🎯 自定义 Top 55

编辑 `top55.json` 添加你自己的 skills：

```json
{
  "skills": [
    {
      "name": "my-skill",
      "repo": "owner/repo",
      "path": "skills/my-skill",
      "category": "software-development",
      "reason": "为什么选这个skill"
    }
  ]
}
```

## 🔗 同系列项目 — AI Agent 协作开发

这三个项目均由 **Hermes Agent + 土鳖（DeepSeek）双 Agent 协作开发**，是 AI 辅助开发的最佳实践案例。欢迎 Star、Issue、PR！

| 项目 | 描述 | 技术栈 | Stars |
|------|------|--------|-------|
| [**okr-alignment-system**](https://github.com/freshtemp-labs/okr-alignment-system) | OKR 对齐管理系统 — 树状可视化 + 级联计算 + iCloud 同步 | Swift / SwiftUI / CoreData | ![](https://img.shields.io/github/stars/freshtemp-labs/okr-alignment-system) |
| [**ai-compute-map**](https://github.com/freshtemp-labs/ai-compute-map) | 全球 AI 算力供应链地图 — 三层数据可视化 | React / TypeScript / ECharts | ![](https://img.shields.io/github/stars/freshtemp-labs/ai-compute-map) |
| [**ba2plus-calculator**](https://github.com/freshtemp-labs/ba2plus-calculator) | BA II Plus 金融计算器 — CFA 考试就绪 | HTML / JS / Tauri | ![](https://img.shields.io/github/stars/freshtemp-labs/ba2plus-calculator) |

> 💡 **为什么这些项目值得关注？**
> - 完整的 PRD + 代码文档 + 测试覆盖
> - AI Agent 编写的代码经过人工审查和迭代优化
> - 每个项目都有  标签，适合新手贡献者

## 🤝 贡献

欢迎提交 PR 添加更多验证过的 skill 路径到 `top55.json`！

## 📄 License

GPL-3.0 — 与 Hermes Agent 保持一致
