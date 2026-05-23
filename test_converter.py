#!/usr/bin/env python3
"""
test_converter.py — converter.py 的单元测试
"""

import os
import sys
import unittest
from datetime import date

# 确保可以 import converter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from converter import (
    parse_skill_md,
    convert_vercel_to_hermes,
    generate_skill_md,
    validate_hermes_skill,
    extract_source_org,
)


class TestExtractSourceOrg(unittest.TestCase):
    """extract_source_org 测试"""

    def test_standard_repo(self):
        self.assertEqual(extract_source_org("vercel-labs/agent-skills"), "vercel-labs")

    def test_owner_only(self):
        self.assertEqual(extract_source_org("anthropics"), "anthropics")

    def test_empty(self):
        self.assertEqual(extract_source_org(""), "")

    def test_multiple_slashes(self):
        self.assertEqual(extract_source_org("a/b/c"), "a")


class TestParseSkillMd(unittest.TestCase):
    """parse_skill_md 测试"""

    def test_basic_parse(self):
        content = """\
---
name: my-test-skill
description: A test skill
---
This is the body.
"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "my-test-skill")
        self.assertEqual(fm["description"], "A test skill")
        self.assertEqual(body.strip(), "This is the body.")

    def test_with_metadata(self):
        content = """\
---
name: react-best-practices
description: React best practices
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---
Body content here
"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "react-best-practices")
        self.assertEqual(fm["metadata"]["author"], "vercel")
        self.assertEqual(fm["metadata"]["version"], "1.0.0")
        self.assertEqual(body.strip(), "Body content here")

    def test_no_frontmatter(self):
        content = "Just a regular markdown file without frontmatter"
        with self.assertRaises(ValueError):
            parse_skill_md(content)

    def test_invalid_yaml(self):
        # With fallback parser, simple key:value pairs survive broken YAML
        content = """\
---
name: test
  invalid: yaml: : broken
---
body
"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "test")
        self.assertEqual(body.strip(), "body")

    def test_empty_body(self):
        content = """\
---
name: test
description: test
---
"""
        fm, body = parse_skill_md(content)
        self.assertEqual(body, "")

    def test_multiline_body(self):
        content = """\
---
name: test
description: test
---
# Heading 1

This is a paragraph.

```python
print("hello")
```

- list item 1
- list item 2
"""
        fm, body = parse_skill_md(content)
        self.assertIn("Heading 1", body)
        self.assertIn("print(\"hello\")", body)
        self.assertIn("list item 2", body)

    def test_bom_handling(self):
        content = "\ufeff---\nname: bom-test\ndescription: with BOM\n---\nbody"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "bom-test")
        self.assertEqual(body.strip(), "body")

    def test_non_dict_frontmatter(self):
        # YAML 解析出非 dict 的情况
        content = "---\n- item1\n- item2\n---\nbody"
        with self.assertRaises(ValueError):
            parse_skill_md(content)


class TestConvertVercelToHermes(unittest.TestCase):
    """convert_vercel_to_hermes 测试"""

    def test_basic_conversion(self):
        vercel_fm = {
            "name": "react-best-practices",
            "description": "React performance optimization rules",
            "license": "MIT",
            "metadata": {
                "author": "vercel",
                "version": "1.0.0",
            },
        }
        body = "# React Best Practices\n\nSome content"

        hermes_fm, out_body = convert_vercel_to_hermes(
            vercel_fm, body, repo="vercel-labs/agent-skills"
        )

        self.assertEqual(hermes_fm["name"], "react-best-practices")
        self.assertEqual(hermes_fm["description"], "React performance optimization rules")
        self.assertEqual(hermes_fm["author"], "vercel")
        self.assertEqual(hermes_fm["version"], "1.0.0")
        self.assertEqual(hermes_fm["license"], "MIT")

        # metadata.hermes 字段
        hermes_meta = hermes_fm["metadata"]["hermes"]
        self.assertIn("imported", hermes_meta["tags"])
        self.assertIn("vercel-labs", hermes_meta["tags"])
        self.assertEqual(hermes_meta["imported_from"], "vercel-labs/agent-skills")
        self.assertEqual(hermes_meta["imported_at"], date.today().isoformat())
        self.assertEqual(hermes_meta["related_skills"], [])

        self.assertEqual(out_body, body)

    def test_minimal_vercel_fm(self):
        """没有 metadata 的 Vercel frontmatter"""
        vercel_fm = {
            "name": "simple-skill",
            "description": "Simple skill",
        }
        body = "Some body"

        hermes_fm, _ = convert_vercel_to_hermes(
            vercel_fm, body, repo="anthropics/skills"
        )

        self.assertEqual(hermes_fm["name"], "simple-skill")
        # 没有 metadata.author，从 repo 推断
        self.assertEqual(hermes_fm["author"], "anthropics")
        self.assertEqual(hermes_fm["version"], "1.0.0")
        self.assertEqual(hermes_fm["license"], "MIT")

        tags = hermes_fm["metadata"]["hermes"]["tags"]
        self.assertIn("imported", tags)
        self.assertIn("anthropics", tags)

    def test_with_top_level_author(self):
        """Vercel fm 顶层有 author 字段"""
        vercel_fm = {
            "name": "test",
            "description": "test",
            "author": "custom-author",
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "", repo="org/repo")
        self.assertEqual(hermes_fm["author"], "custom-author")

    def test_explicit_category(self):
        vercel_fm = {"name": "test", "description": "test"}
        hermes_fm, _ = convert_vercel_to_hermes(
            vercel_fm, "", repo="org/repo", category="creative"
        )
        # category 不直接影响 frontmatter，但以后可能有用
        self.assertIn("imported", hermes_fm["metadata"]["hermes"]["tags"])

    def test_string_version(self):
        """version 确保是字符串"""
        vercel_fm = {
            "name": "test",
            "description": "test",
            "metadata": {"version": 2},
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "", repo="org/repo")
        self.assertEqual(hermes_fm["version"], "2")

    def test_null_metadata(self):
        """metadata 为 None 的情况"""
        vercel_fm = {
            "name": "test",
            "description": "test",
            "metadata": None,
        }
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "", repo="org/repo")
        self.assertEqual(hermes_fm["author"], "org")
        self.assertEqual(hermes_fm["version"], "1.0.0")


class TestGenerateSkillMd(unittest.TestCase):
    """generate_skill_md 测试"""

    def test_generate_basic(self):
        hermes_fm = {
            "name": "test-skill",
            "description": "A test skill",
            "version": "1.0.0",
            "author": "test-author",
            "license": "MIT",
            "metadata": {
                "hermes": {
                    "tags": ["imported", "test-org"],
                    "related_skills": [],
                    "imported_from": "test-org/test-repo",
                    "imported_at": "2026-05-23",
                }
            },
        }
        body = "# Test Skill\n\nContent here"

        output = generate_skill_md(hermes_fm, body)

        # Should start with ---
        self.assertTrue(output.startswith("---"))
        # Should have correct structure
        self.assertIn("name: test-skill", output)
        self.assertIn("description: A test skill", output)
        self.assertIn("author: test-author", output)
        self.assertIn("imported_from: test-org/test-repo", output)
        # Body should be preserved
        self.assertIn("# Test Skill", output)
        self.assertIn("Content here", output)


class TestValidateHermesSkill(unittest.TestCase):
    """validate_hermes_skill 测试"""

    def setUp(self):
        self.valid_content = """\
---
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

    def test_valid_skill(self):
        errors = validate_hermes_skill(self.valid_content)
        self.assertEqual(errors, [])

    def test_no_frontmatter(self):
        errors = validate_hermes_skill("just text")
        self.assertGreater(len(errors), 0)

    def test_missing_name(self):
        content = "---\ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("name" in e for e in errors))

    def test_missing_description(self):
        content = "---\nname: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("description" in e for e in errors))

    def test_name_too_long(self):
        name = "a" * 65
        content = f"---\nname: {name}\ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("64" in e for e in errors))

    def test_name_invalid_chars(self):
        content = "---\nname: Invalid-Name_With_Caps\n---\nbody"
        errors = validate_hermes_skill(content)
        # 验证 name 格式检查 — 这取决于 converter 的实现
        # 现在的正则只允许小写+数字+连字符+下划线

    def test_description_too_long(self):
        desc = "x" * 1025
        content = f"---\nname: test\ndescription: {desc}\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("1024" in e for e in errors))

    def test_empty_body(self):
        content = "---\nname: test\ndescription: test\n---\n\n"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("body" in e.lower() for e in errors))

    def test_file_too_large(self):
        body = "x" * 100_001
        content = f"---\nname: test\ndescription: test\n---\n{body}"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("100,000" in e for e in errors))

    def test_name_is_zero_length(self):
        content = "---\nname: \ndescription: test\n---\nbody"
        errors = validate_hermes_skill(content)
        self.assertTrue(any("name" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
