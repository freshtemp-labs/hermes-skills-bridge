#!/usr/bin/env python3
"""
bridge.py — Hermes Skills Bridge CLI

将 Vercel npx skills 生态的 SKILL.md 转化为 Hermes Agent 原生格式。

子命令:
  import       从 GitHub 导入单个 skill
  batch-import 批量导入多个 skills (JSON 配置)
  list         列出已导入的 skills
  validate     验证 skill 格式
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# 确保可以从同目录 import converter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from converter import (
    parse_skill_md,
    convert_vercel_to_hermes,
    generate_skill_md,
    validate_hermes_skill,
    extract_source_org,
)

HERMES_SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
GITHUB_RAW = "https://raw.githubusercontent.com"


# ─── 工具函数 ───────────────────────────────────────────────


def _fetch_raw_github(owner: str, repo: str, path: str) -> str:
    """从 GitHub raw content 获取文件内容"""
    url = f"{GITHUB_RAW}/{owner}/{repo}/main/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-skills-bridge/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            # 尝试 UTF-8 解码
            return raw.decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 尝试 master 分支
            url = f"{GITHUB_RAW}/{owner}/{repo}/master/{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "hermes-skills-bridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        raise
    except Exception as e:
        raise RuntimeError(f"无法从 GitHub 获取 {owner}/{repo}/{path}: {e}")


def _fetch_skill_list(owner: str, repo: str, skill_path: str) -> list:
    """
    获取 skill 目录下的文件列表。
    skill_path 可以是目录（含 SKILL.md）或直接指向 SKILL.md 文件。
    """
    result = []
    skill_path = skill_path.rstrip("/")

    # 如果是目录路径（不以 .md 结尾），尝试 SKILL.md
    if not skill_path.endswith(".md"):
        paths_to_try = [
            f"{skill_path}/SKILL.md",
            skill_path,  # 可能本身就是文件路径
        ]
    else:
        paths_to_try = [skill_path]

    found = False
    for sp in paths_to_try:
        try:
            _fetch_raw_github(owner, repo, sp)
            result.append({"path": sp, "type": "file"})
            found = True
            break
        except (RuntimeError, urllib.error.HTTPError):
            continue

    if not found:
        raise RuntimeError(f"在 {owner}/{repo} 中找不到 skill (tried: {paths_to_try})")

    # 尝试 scripts 目录下文件 (常见于 Vercel skills)
    base = skill_path.rstrip("/")
    if not base.endswith(".md"):
        for script_name in ["scripts/requirements.txt", "scripts/run.sh", "scripts/setup.sh"]:
            try:
                _fetch_raw_github(owner, repo, f"{base}/{script_name}")
                result.append({"path": f"{base}/{script_name}", "type": "file"})
            except (RuntimeError, urllib.error.HTTPError):
                pass

    return result


def _import_single_skill(
    owner_repo: str,
    skill_name: str,
    skill_path: Optional[str] = None,
    category: str = "imported",
    target_dir: Optional[str] = None,
) -> dict:
    """
    导入单个 skill 到 Hermes。

    Args:
        owner_repo: "owner/repo"
        skill_name: 导入后的 skill 名称
        skill_path: 仓库中的路径（如 skills/react-best-practices），默认 skills/{skill_name}
        category: Hermes 分类
        target_dir: Hermes skills 目录（默认 ~/.hermes/skills）

    Returns:
        {"name": str, "path": str, "success": bool, "errors": list, "warnings": list}
    """
    if target_dir is None:
        target_dir = HERMES_SKILLS_DIR

    parts = owner_repo.split("/")
    if len(parts) != 2:
        return {"name": skill_name, "path": "", "success": False, "errors": [f"无效的仓库格式: {owner_repo} (需要 owner/repo)"], "warnings": []}

    owner, repo = parts
    result = {"name": skill_name, "path": "", "success": False, "errors": [], "warnings": []}

    # 1. 获取 SKILL.md
    repo_skill_path = skill_path if skill_path else f"skills/{skill_name}"
    try:
        files = _fetch_skill_list(owner, repo, repo_skill_path)
    except RuntimeError as e:
        result["errors"].append(str(e))
        return result

    skill_md_files = [f for f in files if f["path"].endswith("SKILL.md") or f["path"].endswith(".md")]
    if not skill_md_files:
        result["errors"].append(f"在 {owner}/{repo} 中找不到 SKILL.md")
        return result

    skill_content = _fetch_raw_github(owner, repo, skill_md_files[0]["path"])

    # 2. 解析 Vercel 格式
    try:
        vercel_fm, body = parse_skill_md(skill_content)
    except ValueError as e:
        result["errors"].append(f"无法解析 SKILL.md: {e}")
        return result

    # 3. 转化为 Hermes 格式
    hermes_fm, body = convert_vercel_to_hermes(vercel_fm, body, repo=owner_repo, category=category)

    # 4. 覆盖 name（JSON 配置中的 name 优先级更高）
    # vercel_fm 和 skill_name 可能不同（如 vercel 原始名是 react-best-practices
    # 但 JSON 配置指定 vercel-react-best-practices 来避免同名冲突）
    if skill_name and skill_name != hermes_fm.get("name"):
        hermes_fm["name"] = skill_name

    # 5. 生成最终 SKILL.md
    output_content = generate_skill_md(hermes_fm, body)

    # 6. 验证
    validation_errors = validate_hermes_skill(output_content)
    if validation_errors:
        result["warnings"].append(f"生成的 SKILL.md 验证警告: {', '.join(validation_errors)}")

    # 7. 写入目标目录
    target_skill_name = hermes_fm.get("name", skill_name)
    skill_dir = os.path.join(target_dir, category, target_skill_name)
    os.makedirs(skill_dir, exist_ok=True)

    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(output_content)

    result["path"] = skill_md_path

    # 8. 复制 scripts/ 目录
    script_base = repo_skill_path.rstrip("/")
    script_files = [f for f in files if f["path"].startswith(f"{script_base}/scripts/")]
    if script_files:
        scripts_dir = os.path.join(skill_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        for sf in script_files:
            rel_path = os.path.relpath(sf["path"], script_base)
            target_script_path = os.path.join(scripts_dir, rel_path)
            os.makedirs(os.path.dirname(target_script_path), exist_ok=True)
            try:
                content = _fetch_raw_github(owner, repo, sf["path"])
                with open(target_script_path, "w", encoding="utf-8") as f:
                    f.write(content)
                result["warnings"].append(f"已复制脚本: {rel_path}")
            except Exception as e:
                result["warnings"].append(f"无法复制脚本 {rel_path}: {e}")

    result["success"] = True
    return result


# ─── CLI 命令 ────────────────────────────────────────────────


def cmd_import(args: argparse.Namespace) -> int:
    """bridge.py import <owner/repo> [--skill SKILL] [--path PATH] [--category CAT]"""
    skill_name = args.skill
    category = args.category or "imported"
    skill_path = getattr(args, "path", None)

    result = _import_single_skill(
        args.owner_repo, skill_name,
        skill_path=skill_path,
        category=category,
    )

    if result["success"]:
        print(f"✅ 导入成功: {result['name']}")
        print(f"   路径: {result['path']}")
    else:
        print(f"❌ 导入失败: {result['name']}")
        for err in result["errors"]:
            print(f"   ⚠ {err}")
        return 1

    for warn in result["warnings"]:
        print(f"   {warn}")

    return 0


def cmd_batch_import(args: argparse.Namespace) -> int:
    """bridge.py batch-import <json-file>"""
    json_path = args.json_file

    with open(json_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    skills = config.get("skills", [])
    if not skills:
        print("❌ JSON 配置中找不到 skills 列表")
        return 1

    print(f"开始批量导入 {len(skills)} 个 skills...")
    print()

    success_count = 0
    fail_count = 0

    for i, skill_cfg in enumerate(skills, 1):
        name = skill_cfg.get("name", "unknown")
        repo = skill_cfg.get("repo", "unknown")
        category = skill_cfg.get("category", "imported")
        reason = skill_cfg.get("reason", "")

        print(f"[{i}/{len(skills)}] {name} ({repo})")
        if reason:
            print(f"      原因: {reason}")

        result = _import_single_skill(
            repo, name,
            skill_path=skill_cfg.get("path"),
            category=category,
        )

        if result["success"]:
            print(f"      ✅ 导入成功 → {result['path']}")
            success_count += 1
        else:
            print(f"      ❌ 导入失败")
            for err in result["errors"]:
                print(f"         ⚠ {err}")
            fail_count += 1

        for warn in result.get("warnings", []):
            print(f"         ℹ {warn}")

        print()

    print(f"批量导入完成: {success_count} 成功, {fail_count} 失败")

    if fail_count > 0:
        return 1
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """bridge.py list"""
    skills_dir = HERMES_SKILLS_DIR

    if not os.path.isdir(skills_dir):
        print("~/.hermes/skills/ 目录不存在")
        return 0

    # 遍历所有分类目录
    imported_skills = []

    for category in sorted(os.listdir(skills_dir)):
        cat_path = os.path.join(skills_dir, category)
        if not os.path.isdir(cat_path):
            continue
        for sk_name in sorted(os.listdir(cat_path)):
            sk_md = os.path.join(cat_path, sk_name, "SKILL.md")
            if os.path.isfile(sk_md):
                try:
                    fm, _ = parse_skill_md(open(sk_md, "r", encoding="utf-8").read())
                    imported_from = ""
                    meta_hermes = fm.get("metadata", {}).get("hermes", {})
                    if meta_hermes:
                        imported_from = meta_hermes.get("imported_from", "")
                    imported_skills.append((category, sk_name, imported_from, sk_md))
                except (ValueError, OSError):
                    imported_skills.append((category, sk_name, "?", sk_md))

    if not imported_skills:
        print("~/.hermes/skills/ 中没有已导入的 skills")
        return 0

    print(f"共 {len(imported_skills)} 个 skills:\n")

    # 按 category 分组显示
    current_cat = None
    for cat, name, imp_from, path in imported_skills:
        if cat != current_cat:
            print(f"\n  [{cat}]")
            current_cat = cat
        is_imported = " ⬇" if imp_from else ""
        imported_label = f" (from {imp_from})" if imp_from else ""
        print(f"    {name}{imported_label}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """bridge.py validate <name>"""
    target = args.name

    # 搜索 skill 文件
    skills_dir = HERMES_SKILLS_DIR

    if not os.path.isdir(skills_dir):
        print(f"❌ {skills_dir} 不存在")
        return 1

    # 查找匹配
    candidates = []
    for category in os.listdir(skills_dir):
        cat_path = os.path.join(skills_dir, category)
        if not os.path.isdir(cat_path):
            continue
        for sk_name in os.listdir(cat_path):
            if sk_name == target:
                sk_md = os.path.join(cat_path, sk_name, "SKILL.md")
                if os.path.isfile(sk_md):
                    candidates.append((category, sk_name, sk_md))

    if not candidates:
        print(f"❌ 找不到名为 '{target}' 的 skill")
        return 1

    all_pass = True
    for category, name, path in candidates:
        content = open(path, "r", encoding="utf-8").read()
        errors = validate_hermes_skill(content)

        if errors:
            print(f"❌ [{category}/{name}] 验证失败:")
            for e in errors:
                print(f"   ⚠ {e}")
            all_pass = False
        else:
            print(f"✅ [{category}/{name}] 格式正确")
            # 显示基本信息
            try:
                fm, body = parse_skill_md(content)
                print(f"   name:        {fm.get('name', '?')}")
                print(f"   description: {textwrap.shorten(fm.get('description', '?'), width=60)}")
                print(f"   author:      {fm.get('author', '?')}")
                print(f"   version:     {fm.get('version', '?')}")
                print(f"   body 长度:   {len(body.strip())} chars")
                print(f"   总大小:      {len(content)} chars ({len(content.encode('utf-8'))} bytes)")
            except Exception as e:
                print(f"   ⚠ 读取额外信息失败: {e}")

    return 0 if all_pass else 1


# ─── 入口 ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Hermes Skills Bridge — Vercel → Hermes skill 转化器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            示例:
              python3 bridge.py import vercel-labs/agent-skills --skill react-best-practices --category software-development
              python3 bridge.py batch-import top10.json
              python3 bridge.py list
              python3 bridge.py validate react-best-practices
        """),
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # import
    p_import = subparsers.add_parser("import", help="从 GitHub 导入单个 skill")
    p_import.add_argument("owner_repo", help="GitHub 仓库 (owner/repo)")
    p_import.add_argument("-s", "--skill", required=True, help="skill 名称")
    p_import.add_argument("-p", "--path", default=None, help="仓库中的路径 (如 skills/my-skill)，默认 skills/<skill-name>")
    p_import.add_argument("-c", "--category", default="imported", help="Hermes 分类 (默认: imported)")
    p_import.set_defaults(func=cmd_import)

    # batch-import
    p_batch = subparsers.add_parser("batch-import", help="从 JSON 配置批量导入 skills")
    p_batch.add_argument("json_file", help="JSON 配置文件路径")
    p_batch.set_defaults(func=cmd_batch_import)

    # list
    p_list = subparsers.add_parser("list", help="列出已导入的 skills")
    p_list.set_defaults(func=cmd_list)

    # validate
    p_validate = subparsers.add_parser("validate", help="验证 skill 格式")
    p_validate.add_argument("name", help="skill 名称")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
