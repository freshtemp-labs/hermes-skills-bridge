"""
converter.py — Vercel SKILL.md → Hermes SKILL.md 格式转化器
"""
import re
import yaml
from datetime import date
from typing import Optional


def parse_skill_md(content: str) -> tuple[dict, str]:
    """解析 SKILL.md，返回 (frontmatter_dict, body_markdown)"""
    content = content.lstrip('\ufeff')  # 去掉 BOM
    
    # 匹配 YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not match:
        raise ValueError("找不到 YAML frontmatter（文件必须以 --- 开头）")
    
    fm_text = match.group(1)
    body = match.group(2)
    
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {e}")
    
    if not isinstance(fm, dict):
        raise ValueError("frontmatter 必须是字典格式")
    
    return fm, body


def extract_source_org(repo: str) -> str:
    """从 owner/repo 提取 org 名"""
    return repo.split('/')[0] if '/' in repo else repo


def convert_vercel_to_hermes(
    vercel_fm: dict,
    body: str,
    repo: str = "unknown",
    category: str = "imported"
) -> tuple[dict, str]:
    """
    将 Vercel 格式的 frontmatter 转化为 Hermes 格式。
    返回 (hermes_frontmatter, body)
    """
    # 基础字段
    name = vercel_fm.get('name', '')
    description = vercel_fm.get('description', '')
    license_val = vercel_fm.get('license', 'MIT')
    
    # 从 metadata 提取
    metadata = vercel_fm.get('metadata', {}) or {}
    author = metadata.get('author', vercel_fm.get('author', extract_source_org(repo)))
    version = metadata.get('version', vercel_fm.get('version', '1.0.0'))
    
    # 确保 version 是字符串
    version = str(version)
    
    # 构建 Hermes frontmatter
    hermes_fm = {
        'name': name,
        'description': description,
        'version': version,
        'author': author,
        'license': license_val,
        'metadata': {
            'hermes': {
                'tags': ['imported', extract_source_org(repo)],
                'related_skills': [],
                'imported_from': repo,
                'imported_at': date.today().isoformat(),
            }
        }
    }
    
    return hermes_fm, body


def generate_skill_md(hermes_fm: dict, body: str) -> str:
    """生成 Hermes 格式的 SKILL.md 内容"""
    fm_yaml = yaml.dump(hermes_fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_yaml}---\n\n{body}"


def validate_hermes_skill(content: str) -> list:
    """验证 Hermes skill 格式，返回错误列表（空=通过）"""
    errors = []
    
    if not content.startswith('---'):
        errors.append("文件必须以 '---' 开头")
        return errors
    
    try:
        fm, body = parse_skill_md(content)
    except ValueError as e:
        errors.append(str(e))
        return errors
    
    # name 检查
    name = fm.get('name', '')
    if not name:
        errors.append("缺少 name 字段")
    elif len(name) > 64:
        errors.append(f"name 过长 ({len(name)} > 64)")
    elif not re.match(r'^[a-z0-9][a-z0-9_-]*$', name):
        errors.append(f"name 格式不合规: '{name}' (需要小写+连字符/下划线)")
    
    # description 检查
    desc = fm.get('description', '')
    if not desc:
        errors.append("缺少 description 字段")
    elif len(desc) > 1024:
        errors.append(f"description 过长 ({len(desc)} > 1024)")
    
    # body 检查
    if not body.strip():
        errors.append("body 不能为空")
    
    # 总大小检查
    if len(content) > 100_000:
        errors.append(f"文件过大 ({len(content)} > 100,000)")
    
    return errors
