# PRD: Hermes Skills Bridge

## 目标
构建 Python CLI 工具，将 Vercel `npx skills` 生态的 SKILL.md 转化为 Hermes Agent 原生格式。

## 核心功能

### 1. `bridge.py import <owner/repo> --skill <name>`
- 从 GitHub 仓库 clone/fetch 指定 skill 的 SKILL.md
- 解析 Vercel YAML frontmatter
- 转化为 Hermes 格式（字段映射见下方）
- 写入 `~/.hermes/skills/<category>/<name>/SKILL.md`
- 如果 skill 有 scripts/ 目录，一并复制

### 2. `bridge.py batch-import <json-file>`
- 读取 JSON 配置文件（含 repo、path、category）
- 逐个调用 import 逻辑
- 输出转化报告

### 3. `bridge.py list`
- 列出 `~/.hermes/skills/` 下所有已导入的 skills
- 标记哪些是从 Vercel 生态导入的（通过 metadata.hermes.imported_from）

### 4. `bridge.py validate <name>`
- 验证指定 skill 的 SKILL.md 是否符合 Hermes 格式规范
- 检查：frontmatter 完整性、name 长度≤64、description≤1024、总大小≤100K

## 字段映射规则

### Vercel → Hermes frontmatter

```yaml
# Vercel 格式
---
name: react-best-practices
description: React性能优化指南...
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---

# 转化为 Hermes 格式
---
name: react-best-practices
description: React性能优化指南...
version: 1.0.0
author: vercel
license: MIT
metadata:
  hermes:
    tags: [imported, vercel]
    related_skills: []
    imported_from: vercel-labs/agent-skills
    imported_at: "2026-05-23"
---
```

### 转化规则
1. `name` → 直接映射（验证≤64字符，小写+连字符）
2. `description` → 直接映射（验证≤1024字符）
3. `metadata.author` → 提升为顶层 `author`
4. `metadata.version` → 提升为顶层 `version`
5. `license` → 直接映射
6. 新增 `metadata.hermes.tags` = [imported, <source-org>]
7. 新增 `metadata.hermes.imported_from` = owner/repo
8. 新增 `metadata.hermes.imported_at` = ISO日期
9. Markdown body → 原样保留

## 测试标准

对 top10.json 中的每个 skill：
1. ✅ import 成功，无报错
2. ✅ 生成的 SKILL.md 通过 validate
3. ✅ `skill_view(name)` 能正确加载
4. ✅ 内容完整（对比原文，无截断）
5. ✅ scripts/ 目录（如有）正确复制

## 文件结构

```
~/Desktop/hermes-skills-bridge/
├── README.md
├── PRD.md
├── bridge.py          # 主CLI工具
├── converter.py       # 格式转化逻辑
├── top10.json         # Top 10 skills 配置
├── tests/             # 测试
│   ├── test_converter.py
│   └── test_import.py
└── _reference/        # 参考仓库（不提交）
    ├── vercel-skills/
    ├── agent-skills/
    └── skills/
```
