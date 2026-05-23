# Hermes Skills Bridge

> 让 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 一键用上 [skills.sh](https://skills.sh) 生态的 500+ AI Agent Skills

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://python.org)
[![Skills Imported](https://img.shields.io/badge/Skills%20Imported-50-green.svg)](top50.json)

## 🚀 一行命令，500+ Skills

```bash
# 导入单个 skill
python3 bridge.py import anthropics/skills --skill frontend-design

# 批量导入 Top 50
python3 bridge.py batch-import top50.json

# 查看已导入
python3 bridge.py list

# 验证格式
python3 bridge.py validate
```

## 📦 已验证的 Top 50 Skills

来自 **13 个高质量仓库**，覆盖 **5 大类别**：

| 类别 | 数量 | 来源 |
|------|------|------|
| 🎨 Creative | 14 | anthropics, vercel-labs, op7418, blader, JuliusBrussee... |
| 💻 Software Development | 12 | vercel-labs, anthropics, SawyerHood, lackeyjb... |
| 🔬 Research | 10 | lijigang, elementalsouls |
| 📄 Productivity | 9 | lijigang, OthmanAdi, nidhinjs, zarazhangrui... |
| 🛠 DevOps | 1 | vercel-labs |

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

## 🎯 自定义 Top 50

编辑 `top50.json` 添加你自己的 skills：

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

## 🤝 贡献

欢迎提交 PR 添加更多验证过的 skill 路径到 `top50.json`！

## 📄 License

GPL-3.0 — 与 Hermes Agent 保持一致
