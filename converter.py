"""
converter.py — Vercel SKILL.md → Hermes SKILL.md 格式转化器
"""
import re
import yaml
from datetime import date
from typing import Optional


# Valid Hermes skill categories
VALID_CATEGORIES = frozenset({
    'creative', 'software-development', 'research', 'productivity',
    'devops', 'mlops', 'data-science', 'red-teaming', 'social-media',
    'media', 'gaming', 'email', 'github', 'note-taking', 'smart-home', 'apple',
})

# Redundant description prefixes to flag
REDUNDANT_DESCRIPTION_PREFIXES = [
    r'^[Aa] skill for\b',
    r'^[Tt]his skill\b',
    r'^[Aa] Claude (Code |)skill\b',
    r'^[Aa]n? agent skill\b',
    r'^[Tt]his is a skill\b',
]


def _normalize_name(name: str) -> str:
    """Normalize a skill name: lowercase, spaces→hyphens, strip special chars."""
    if not name:
        return name
    # Lowercase
    name = name.lower()
    # Replace spaces and underscores with hyphens
    name = re.sub(r'[\s_]+', '-', name)
    # Remove any characters that don't match [a-z0-9_-]
    name = re.sub(r'[^a-z0-9_-]', '', name)
    # Ensure starts with a-z0-9
    name = re.sub(r'^[^a-z0-9]+', '', name)
    # Collapse multiple hyphens
    name = re.sub(r'-{2,}', '-', name)
    # Strip leading/trailing hyphens
    name = name.strip('-')
    return name


def _parse_simple_key_value(text: str) -> dict:
    """Fallback parser for frontmatter that isn't valid YAML but has
    simple key: value pairs (one per line)."""
    result = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Match key: value
        m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$', line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            # Strip quotes
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            result[key] = value
    return result


def parse_skill_md(content: str) -> tuple[dict, str]:
    """解析 SKILL.md，返回 (frontmatter_dict, body_markdown)"""
    # Normalize line endings: CRLF → LF
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    # Strip BOM
    content = content.lstrip('\ufeff')

    # Match YAML frontmatter (the \n before --- is optional for empty frontmatter)
    match = re.match(r'^---\s*\n(.*?)---\s*\n(.*)', content, re.DOTALL)
    if not match:
        raise ValueError("找不到 YAML frontmatter（文件必须以 --- 开头）")

    fm_text = match.group(1)
    body = match.group(2)

    # Handle empty frontmatter (---\n---)
    if not fm_text.strip():
        fm = {}
    else:
        fm = None
        # Try YAML first
        try:
            fm = yaml.safe_load(fm_text)
        except yaml.YAMLError:
            pass

        # If YAML parsing failed or returned non-dict, try simple key:value fallback
        if not isinstance(fm, dict):
            fm = _parse_simple_key_value(fm_text)

        # If still empty or non-dict, error out
        if not isinstance(fm, dict):
            raise ValueError("frontmatter 必须是字典格式")
        if not fm:
            raise ValueError("frontmatter 解析结果为空")

    # Normalize "name" field
    if 'name' in fm:
        raw_name = fm['name']
        if raw_name is None:
            fm['name'] = ''
        else:
            fm['name'] = _normalize_name(str(raw_name))

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
    # Known fields in Vercel format
    known_keys = {'name', 'description', 'license', 'metadata', 'author',
                  'version', 'tags', 'category', 'platforms'}

    # Extract known fields
    name = vercel_fm.get('name', '')
    description = vercel_fm.get('description', '')
    license_val = vercel_fm.get('license', 'MIT')

    # Handle metadata — could be a string or dict
    metadata = vercel_fm.get('metadata', {}) or {}
    if isinstance(metadata, str):
        metadata = {'raw_metadata': metadata}
    if not isinstance(metadata, dict):
        metadata = {}

    author = metadata.get('author', vercel_fm.get('author', extract_source_org(repo)))
    version = metadata.get('version', vercel_fm.get('version', '1.0.0'))
    # Ensure version is string
    version = str(version)

    # Build Hermes frontmatter — starting with known fields
    hermes_fm = {
        'name': name,
        'description': description,
        'version': version,
        'author': author,
        'license': license_val,
    }

    # Preserve category from original frontmatter if present
    if 'category' in vercel_fm:
        hermes_fm['category'] = vercel_fm['category']

    # Convert platforms list to Hermes platform field
    if 'platforms' in vercel_fm and isinstance(vercel_fm['platforms'], list):
        hermes_fm['platform'] = ', '.join(vercel_fm['platforms'])

    # Preserve any unknown/original fields not in known_keys
    for key, value in vercel_fm.items():
        if key not in known_keys and key not in hermes_fm:
            hermes_fm[key] = value

    # Build Hermes metadata
    hermes_fm['metadata'] = {
        'hermes': {
            'tags': ['imported', extract_source_org(repo)],
            'related_skills': [],
            'imported_from': repo,
            'imported_at': date.today().isoformat(),
        }
    }

    # Preserve any extra original metadata keys under hermes metadata
    if metadata:
        for k, v in metadata.items():
            if k not in hermes_fm['metadata']['hermes']:
                hermes_fm['metadata'][k] = v

    return hermes_fm, body


def generate_skill_md(hermes_fm: dict, body: str) -> str:
    """生成 Hermes 格式的 SKILL.md 内容"""
    fm_yaml = yaml.dump(hermes_fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_yaml}---\n\n{body}"


def validate_hermes_skill(content: str, category: Optional[str] = None) -> list:
    """验证 Hermes skill 格式，返回错误列表（空=通过）

    Args:
        content: SKILL.md 文件内容
        category: 可选，技能所属分类（用于验证 category 是否合法）
    """
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
    else:
        if len(desc) > 1024:
            errors.append(f"description 过长 ({len(desc)} > 1024)")
        # Check for redundant prefixes
        for prefix_pattern in REDUNDANT_DESCRIPTION_PREFIXES:
            m = re.match(prefix_pattern, desc)
            if m:
                errors.append(
                    f"description 包含冗余前缀: '{desc[:50]}...' — "
                    f"请直接描述功能，不要以 '{m.group(0)}' 开头"
                )
                break

    # body 检查
    if not body.strip():
        errors.append("body 不能为空")

    # 总大小检查
    if len(content) > 100_000:
        errors.append(f"文件过大 ({len(content)} > 100,000)")

    # Category 检查（如果提供了）
    if category is not None:
        if category not in VALID_CATEGORIES:
            errors.append(
                f"category '{category}' 不合法，有效值: "
                f"{', '.join(sorted(VALID_CATEGORIES))}"
            )

    return errors
