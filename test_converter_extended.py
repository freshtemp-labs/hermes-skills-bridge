"""
test_converter_extended.py — Extended edge case tests for converter.py
"""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from converter import (
    parse_skill_md,
    convert_vercel_to_hermes,
    generate_skill_md,
    validate_hermes_skill,
    _normalize_name,
    _parse_simple_key_value,
    VALID_CATEGORIES,
)


class TestNormalizeName(unittest.TestCase):
    """_normalize_name 测试"""

    def test_lowercase(self):
        self.assertEqual(_normalize_name("React"), "react")

    def test_spaces_to_hyphens(self):
        self.assertEqual(_normalize_name("My Cool Skill"), "my-cool-skill")

    def test_mixed_case_and_spaces(self):
        self.assertEqual(_normalize_name("React Best Practices"), "react-best-practices")

    def test_already_valid(self):
        self.assertEqual(_normalize_name("my-skill"), "my-skill")

    def test_underscores(self):
        self.assertEqual(_normalize_name("my_skill_name"), "my-skill-name")

    def test_special_chars_removed(self):
        self.assertEqual(_normalize_name("skill (v2)!"), "skill-v2")

    def test_empty(self):
        self.assertEqual(_normalize_name(""), "")

    def test_only_special(self):
        self.assertEqual(_normalize_name("!@#$%"), "")

    def test_leading_hyphens_stripped(self):
        self.assertEqual(_normalize_name("-my-skill"), "my-skill")

    def test_multiple_hyphens_collapsed(self):
        self.assertEqual(_normalize_name("my---skill"), "my-skill")


class TestParseSimpleKeyValue(unittest.TestCase):
    """_parse_simple_key_value 测试"""

    def test_basic_kv(self):
        result = _parse_simple_key_value("name: test\nversion: 1.0")
        self.assertEqual(result, {"name": "test", "version": "1.0"})

    def test_quoted_value(self):
        result = _parse_simple_key_value('name: "hello world"\ndescription: "A test"')
        self.assertEqual(result, {"name": "hello world", "description": "A test"})

    def test_single_quoted_value(self):
        result = _parse_simple_key_value("name: 'hello'")
        self.assertEqual(result, {"name": "hello"})

    def test_empty_lines_skipped(self):
        result = _parse_simple_key_value("name: test\n\nversion: 2")
        self.assertEqual(result, {"name": "test", "version": "2"})

    def test_comment_lines_skipped(self):
        result = _parse_simple_key_value("name: test\n# comment\nversion: 1")
        self.assertEqual(result, {"name": "test", "version": "1"})

    def test_empty_input(self):
        result = _parse_simple_key_value("")
        self.assertEqual(result, {})


class TestParseSkillMdEdgeCases(unittest.TestCase):
    """parse_skill_md 边界情况测试"""

    # ── CRLF 行尾测试 ──
    def test_crlf_line_endings(self):
        content = "---\r\nname: crlf-test\r\ndescription: with CRLF\r\n---\r\nBody here"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "crlf-test")
        self.assertEqual(body.strip(), "Body here")

    def test_cr_only_line_endings(self):
        content = "---\rname: cr-test\rdescription: with CR\r---\rBody here"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "cr-test")
        self.assertEqual(body.strip(), "Body here")

    # ── 空 frontmatter 测试 ──
    def test_empty_frontmatter(self):
        content = "---\n---\nBody with empty frontmatter"
        fm, body = parse_skill_md(content)
        self.assertEqual(body.strip(), "Body with empty frontmatter")

    def test_whitespace_only_frontmatter(self):
        content = "---\n   \n---\nBody here"
        fm, body = parse_skill_md(content)
        self.assertEqual(body.strip(), "Body here")

    # ── Name 标准化测试 ──
    def test_name_with_spaces(self):
        content = "---\nname: My Cool Skill\ndescription: test\n---\nbody"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "my-cool-skill")

    def test_name_with_uppercase(self):
        content = "---\nname: ReactBestPractices\ndescription: test\n---\nbody"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "reactbestpractices")

    def test_name_already_valid(self):
        content = "---\nname: valid-name\ndescription: test\n---\nbody"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "valid-name")

    # ── 非标准 YAML 但有关键值对的 fallback 测试 ──
    def test_invalid_yaml_with_simple_kv(self):
        content = """---
name: my-skill
description: A skill with broken YAML
  this is: clearly not valid yaml but has key value above
---
Body"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "my-skill")
        self.assertEqual(body.strip(), "Body")

    def test_yaml_with_special_chars_in_value(self):
        content = """---
name: test-skill
description: Contains special chars: !@#$%
---
Body"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "test-skill")
        self.assertEqual(body.strip(), "Body")

    # ── 复杂 YAML 仍然正常工作 ──
    def test_complex_yaml_still_works(self):
        content = """---
name: complex-skill
description: Complex YAML test
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
  tags:
    - react
    - nextjs
---
Body with complex frontmatter"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "complex-skill")
        self.assertEqual(fm["metadata"]["author"], "vercel")
        self.assertEqual(fm["metadata"]["version"], "1.0.0")
        self.assertEqual(len(fm["metadata"]["tags"]), 2)


class TestConvertVercelToHermesExtended(unittest.TestCase):
    """convert_vercel_to_hermes 扩展测试"""

    # ── 保留未知字段 ──
    def test_preserve_unknown_fields(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "custom_field": "custom_value",
            "another_custom": 42,
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["custom_field"], "custom_value")
        self.assertEqual(hermes_fm["another_custom"], 42)

    # ── 保留 category ──
    def test_preserve_category_from_frontmatter(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "category": "creative",
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["category"], "creative")

    def test_category_not_overwritten_by_repo_category(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "category": "creative",
        }
        hermes_fm, _ = convert_vercel_to_hermes(
            vercel_fm, "body", repo="org/repo", category="software-development"
        )
        # Frontmatter category takes precedence
        self.assertEqual(hermes_fm["category"], "creative")

    # ── platforms 转换 ──
    def test_platforms_list_converted(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "platforms": ["linux", "macos", "windows"],
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["platform"], "linux, macos, windows")

    def test_single_platform(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "platforms": ["web"],
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["platform"], "web")

    def test_no_platforms_field(self):
        vercel_fm = {"name": "test", "description": "test"}
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertNotIn("platform", hermes_fm)

    # ── metadata 为字符串 ──
    def test_metadata_is_string(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "metadata": "some string metadata",
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["author"], "org")  # Falls back to repo org
        self.assertEqual(hermes_fm["version"], "1.0.0")

    def test_metadata_is_empty_string(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "metadata": "",
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["author"], "org")
        self.assertEqual(hermes_fm["version"], "1.0.0")

    # ── 保留额外 metadata 键 ──
    def test_preserve_extra_metadata_keys(self):
        vercel_fm = {
            "name": "test",
            "description": "test",
            "metadata": {
                "author": "test-author",
                "version": "1.0.0",
                "extra_info": "preserved",
            },
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "body", repo="org/repo")
        self.assertEqual(hermes_fm["metadata"]["extra_info"], "preserved")


class TestValidateHermesSkillExtended(unittest.TestCase):
    """validate_hermes_skill 扩展测试"""

    def setUp(self):
        self.valid_content = """---
name: valid-skill
description: This is a valid skill description
version: 1.0.0
author: test
license: MIT
metadata:
  hermes:
    tags: [imported, test]
    related_skills: []
    imported_from: test/test
    imported_at: "2026-05-23"
---
# Valid Skill

Body content here.
"""

    # ── name 格式验证 ──
    def test_name_matches_pattern(self):
        errors = validate_hermes_skill(self.valid_content)
        self.assertEqual(errors, [])

    def test_name_starts_with_number(self):
        # Should be valid: pattern allows starting with a-z or 0-9
        content = "---\nname: 2fa-auth\ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertFalse(any("name" in e.lower() and "格式" in e for e in errors),
                         f"Name starting with number should be valid, got: {errors}")

    def test_name_with_invalid_chars(self):
        # Name with characters that survive normalization but break the pattern
        # The name normalizer strips most special chars, so use a name that
        # normalizes to something still invalid (e.g., starts with hyphen after strip)
        content = "---\nname: !!!\ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        # After normalization, "!!!" becomes "" which triggers "missing name"
        self.assertTrue(any("name" in e.lower() for e in errors),
                        f"Expected name error, got: {errors}")

    def test_name_exactly_64_chars(self):
        name = "a" * 64
        content = f"---\nname: {name}\ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertFalse(any("name" in e.lower() and "过长" in e for e in errors),
                         f"64-char name should be valid, got: {errors}")

    def test_name_exceeds_64_chars(self):
        name = "a" * 65
        content = f"---\nname: {name}\ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("64" in e for e in errors),
                        f"Expected name too long error, got: {errors}")

    # ── description 长度验证 ──
    def test_description_exactly_1024_chars(self):
        desc = "x" * 1024
        content = f"---\nname: test\ndescription: {desc}\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertFalse(any("description" in e.lower() and "过长" in e for e in errors),
                         f"1024-char description should be valid, got: {errors}")

    def test_description_exceeds_1024_chars(self):
        desc = "x" * 1025
        content = f"---\nname: test\ndescription: {desc}\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("1024" in e for e in errors),
                        f"Expected description too long error, got: {errors}")

    # ── 冗余 description 前缀检测 ──
    def test_description_starts_with_a_skill_for(self):
        content = """---
name: test
description: A skill for doing amazing things with AI
---
body"""
        errors = validate_hermes_skill(content)
        self.assertTrue(any("冗余" in e for e in errors),
                        f"Expected redundant prefix error, got: {errors}")

    def test_description_starts_with_this_skill(self):
        content = """---
name: test
description: This skill helps you with various tasks
---
body"""
        errors = validate_hermes_skill(content)
        self.assertTrue(any("冗余" in e for e in errors),
                        f"Expected redundant prefix error, got: {errors}")

    def test_description_without_redundant_prefix(self):
        content = """---
name: test
description: Helps you with various tasks using AI
---
body"""
        errors = validate_hermes_skill(content)
        self.assertFalse(any("冗余" in e for e in errors),
                         f"Should not flag non-redundant prefix, got: {errors}")

    # ── category 验证 ──
    def test_valid_category(self):
        errors = validate_hermes_skill(self.valid_content, category="creative")
        self.assertEqual(errors, [])

    def test_valid_category_software_development(self):
        errors = validate_hermes_skill(self.valid_content, category="software-development")
        self.assertEqual(errors, [])

    def test_invalid_category(self):
        errors = validate_hermes_skill(self.valid_content, category="invalid-category")
        self.assertTrue(any("category" in e.lower() for e in errors),
                        f"Expected invalid category error, got: {errors}")

    def test_no_category_provided(self):
        # Should not add any category error when category is None
        errors = validate_hermes_skill(self.valid_content)
        self.assertEqual(errors, [])


class TestRoundTrip(unittest.TestCase):
    """Round-trip 测试"""

    def test_vercel_to_hermes_and_validate(self):
        """完整流程：解析 → 转化 → 生成 → 验证"""
        vercel_skill = """---
name: my-skill
description: A useful skill for developers
license: Apache-2.0
metadata:
  author: johndoe
  version: "2.0.0"
---
# My Skill

This is a great skill.
"""
        fm, body = parse_skill_md(vercel_skill)
        hermes_fm, hermes_body = convert_vercel_to_hermes(
            fm, body, repo="johndoe/my-skills", category="software-development"
        )
        output = generate_skill_md(hermes_fm, hermes_body)
        errors = validate_hermes_skill(output, category="software-development")
        self.assertEqual(errors, [], f"Round-trip failed: {errors}")


if __name__ == "__main__":
    unittest.main()
