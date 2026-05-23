"""test_converter.py — 测试格式转化逻辑"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from converter import (
    parse_skill_md,
    convert_vercel_to_hermes,
    generate_skill_md,
    validate_hermes_skill,
    extract_source_org,
)

# 测试数据
VERCEL_SKILL = """---
name: react-best-practices
description: React and Next.js performance optimization guidelines from Vercel Engineering.
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---

# React Best Practices

Some content here.

## When to Apply

- Writing new React components
- Reviewing code
"""

HERMES_SKILL = """---
name: react-best-practices
description: React and Next.js performance optimization guidelines from Vercel Engineering.
version: '1.0.0'
author: vercel
license: MIT
metadata:
  hermes:
    tags:
    - imported
    - vercel
    related_skills: []
    imported_from: vercel-labs/agent-skills
    imported_at: '2026-05-23'
---

# React Best Practices

Some content here.

## When to Apply

- Writing new React components
- Reviewing code
"""


def test_parse_skill_md():
    fm, body = parse_skill_md(VERCEL_SKILL)
    assert fm['name'] == 'react-best-practices'
    assert 'React' in fm['description']
    assert 'When to Apply' in body
    print("✅ test_parse_skill_md")


def test_parse_with_bom():
    bom_skill = '\ufeff' + VERCEL_SKILL
    fm, body = parse_skill_md(bom_skill)
    assert fm['name'] == 'react-best-practices'
    print("✅ test_parse_with_bom")


def test_parse_no_frontmatter():
    try:
        parse_skill_md("Just some markdown")
        assert False, "Should have raised"
    except ValueError as e:
        assert "frontmatter" in str(e).lower()
    print("✅ test_parse_no_frontmatter")


def test_convert_vercel_to_hermes():
    fm, body = parse_skill_md(VERCEL_SKILL)
    hermes_fm, hermes_body = convert_vercel_to_hermes(
        fm, body, repo="vercel-labs/agent-skills", category="software-development"
    )
    
    assert hermes_fm['name'] == 'react-best-practices'
    assert hermes_fm['author'] == 'vercel'
    assert hermes_fm['version'] == '1.0.0'
    assert hermes_fm['license'] == 'MIT'
    assert 'imported' in hermes_fm['metadata']['hermes']['tags']
    assert hermes_fm['metadata']['hermes']['imported_from'] == 'vercel-labs/agent-skills'
    assert hermes_body == body
    print("✅ test_convert_vercel_to_hermes")


def test_convert_version_number():
    """版本号是数字时也能正确转字符串"""
    fm = {'name': 'test', 'description': 'test', 'metadata': {'version': 2}}
    hermes_fm, _ = convert_vercel_to_hermes(fm, "body")
    assert hermes_fm['version'] == '2'
    print("✅ test_convert_version_number")


def test_extract_source_org():
    assert extract_source_org("vercel-labs/agent-skills") == "vercel-labs"
    assert extract_source_org("anthropics/skills") == "anthropics"
    assert extract_source_org("solo-repo") == "solo-repo"
    print("✅ test_extract_source_org")


def test_generate_skill_md():
    fm, body = parse_skill_md(VERCEL_SKILL)
    hermes_fm, _ = convert_vercel_to_hermes(fm, body, "vercel-labs/agent-skills")
    output = generate_skill_md(hermes_fm, body)
    
    assert output.startswith('---\n')
    assert 'name: react-best-practices' in output
    assert 'imported_from: vercel-labs/agent-skills' in output
    assert '# React Best Practices' in output
    print("✅ test_generate_skill_md")


def test_validate_pass():
    errors = validate_hermes_skill(HERMES_SKILL)
    assert errors == [], f"Expected no errors, got: {errors}"
    print("✅ test_validate_pass")


def test_validate_missing_name():
    bad = "---\ndescription: test\n---\n\nbody"
    errors = validate_hermes_skill(bad)
    assert any("name" in e for e in errors)
    print("✅ test_validate_missing_name")


def test_validate_long_name():
    bad = f"---\nname: {'a' * 65}\ndescription: test\n---\n\nbody"
    errors = validate_hermes_skill(bad)
    assert any("过长" in e for e in errors)
    print("✅ test_validate_long_name")


def test_validate_long_description():
    bad = f"---\nname: test\ndescription: {'a' * 1025}\n---\n\nbody"
    errors = validate_hermes_skill(bad)
    assert any("过长" in e for e in errors)
    print("✅ test_validate_long_description")


def test_validate_empty_body():
    bad = "---\nname: test\ndescription: test\n---\n\n"
    errors = validate_hermes_skill(bad)
    assert any("body" in e.lower() for e in errors)
    print("✅ test_validate_empty_body")


if __name__ == "__main__":
    test_parse_skill_md()
    test_parse_with_bom()
    test_parse_no_frontmatter()
    test_convert_vercel_to_hermes()
    test_convert_version_number()
    test_extract_source_org()
    test_generate_skill_md()
    test_validate_pass()
    test_validate_missing_name()
    test_validate_long_name()
    test_validate_long_description()
    test_validate_empty_body()
    print("\n🎉 全部 12 个测试通过!")
