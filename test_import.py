#!/usr/bin/env python3
"""
test_import.py — bridge.py 的集成测试

使用 unittest.mock 模拟 GitHub 请求，不依赖网络。
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import date

# 确保可以 import bridge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bridge import (
    _fetch_raw_github,
    _fetch_skill_list,
    _import_single_skill,
    cmd_list,
    cmd_validate,
    cmd_import,
    cmd_batch_import,
)
from converter import (
    parse_skill_md,
    convert_vercel_to_hermes,
    generate_skill_md,
    validate_hermes_skill,
)


SAMPLE_SKILL_MD = """\
---
name: react-best-practices
description: React performance optimization guide
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---
# React Best Practices

This is a comprehensive guide for React performance optimization.
"""

SAMPLE_SKILL_BODY = "# React Best Practices\n\nThis is a comprehensive guide for React performance optimization.\n"


class TestParseSkillMdEdgeCases(unittest.TestCase):
    """parse_skill_md 边界情况测试"""

    def test_body_with_extra_frontmatter_markers(self):
        """body 中有 --- 不应该被错误解析"""
        content = """\
---
name: test
description: test
---
Some text with --- in it

```yaml
name: not-frontmatter
```
"""
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "test")
        self.assertIn("not-frontmatter", body)

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            parse_skill_md("")

    def test_only_frontmatter_and_body_separator(self):
        content = "---\nname: test\ndescription: test\n---\n"
        fm, body = parse_skill_md(content)
        self.assertEqual(fm["name"], "test")


class TestGenerateSkillMdEdgeCases(unittest.TestCase):
    """generate_skill_md 边界情况测试"""

    def test_unicode_in_body(self):
        fm = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "license": "MIT",
            "metadata": {"hermes": {"tags": ["imported", "test"], "related_skills": [], "imported_from": "test/repo", "imported_at": "2026-05-23"}},
        }
        body = "# 中文标题\n\n包含 Unicode 字符: → ✓ 🎯"
        output = generate_skill_md(fm, body)
        self.assertIn("中文标题", output)
        self.assertIn("→", output)

    def test_body_with_code_blocks(self):
        fm = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "license": "MIT",
            "metadata": {"hermes": {"tags": ["imported", "test"], "related_skills": [], "imported_from": "test/repo", "imported_at": "2026-05-23"}},
        }
        body = "```python\ndef hello():\n    print('hi')\n```"
        output = generate_skill_md(fm, body)
        self.assertIn("def hello", output)

    def test_parse_then_generate_roundtrip(self):
        """解析后再生成应是可逆的"""
        original_content = """\
---
name: roundtrip-test
description: Testing roundtrip conversion
license: Apache-2.0
metadata:
  author: test-author
  version: "2.0.0"
---
## Section 1

Some content here.

## Section 2

More content.
"""
        fm, body = parse_skill_md(original_content)
        hermes_fm, _ = convert_vercel_to_hermes(
            fm, body, repo="test/repo"
        )
        output = generate_skill_md(hermes_fm, body)

        # 验证可重新解析
        fm2, body2 = parse_skill_md(output)
        self.assertEqual(fm2["name"], "roundtrip-test")
        self.assertEqual(fm2["description"], "Testing roundtrip conversion")
        self.assertEqual(fm2["author"], "test-author")
        self.assertEqual(fm2["version"], "2.0.0")
        self.assertIn("Section 2", body2)


class TestConvertFullPipeline(unittest.TestCase):
    """完整转化流程测试"""

    def test_vercel_to_hermes_full(self):
        vercel_fm, body = parse_skill_md(SAMPLE_SKILL_MD)
        hermes_fm, out_body = convert_vercel_to_hermes(
            vercel_fm, body, repo="vercel-labs/agent-skills"
        )
        result = generate_skill_md(hermes_fm, out_body)

        # 验证
        errors = validate_hermes_skill(result)
        self.assertEqual(errors, [], f"验证应该通过但发现: {errors}")

        # 验证字段
        fm2, body2 = parse_skill_md(result)
        self.assertEqual(fm2["name"], "react-best-practices")
        self.assertEqual(fm2["author"], "vercel")
        self.assertEqual(fm2["metadata"]["hermes"]["imported_from"], "vercel-labs/agent-skills")

    def test_imported_at_date(self):
        """imported_at 应为今天的 ISO 日期"""
        vercel_fm = {"name": "test", "description": "test"}
        hermes_fm, _ = convert_vercel_to_hermes(vercel_fm, "", repo="org/repo")
        self.assertEqual(
            hermes_fm["metadata"]["hermes"]["imported_at"],
            date.today().isoformat()
        )


class TestValidateEdgeCases(unittest.TestCase):
    """validate_hermes_skill 边界测试"""

    def test_no_content(self):
        errors = validate_hermes_skill("")
        self.assertGreater(len(errors), 0)

    def test_only_frontmatter(self):
        content = "---\nname: test\ndescription: test\n---\n"
        errors = validate_hermes_skill(content)
        # body is empty
        self.assertTrue(any("body" in e.lower() for e in errors))

    def test_max_length_boundary(self):
        """description 刚好 1024 字符"""
        desc = "x" * 1024
        content = f"---\nname: test\ndescription: {desc}\n---\nbody"
        errors = validate_hermes_skill(content)
        # 应该没有 description 相关的错误
        desc_errors = [e for e in errors if "description" in e.lower()]
        self.assertEqual(desc_errors, [])


class TestImportSingleSkillDryRun(unittest.TestCase):
    """_import_single_skill 测试（mock 网络请求）"""

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_success(self, mock_fetch_raw, mock_fetch_list):
        mock_fetch_list.return_value = [
            {"path": "skills/test-skill/SKILL.md", "type": "file"},
        ]
        mock_fetch_raw.return_value = """\
---
name: test-skill
description: A test skill
---
# Test

Content here.
"""

        # Use a temp dir as target
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "org/test-repo",
                "test-skill",
                category="software-development",
                target_dir=tmpdir,
            )

            self.assertTrue(result["success"], f"导入失败: {result['errors']}")
            self.assertTrue(os.path.exists(result["path"]))

            # 验证写入的内容
            with open(result["path"], "r") as f:
                content = f.read()
            errors = validate_hermes_skill(content)
            self.assertEqual(errors, [])

            # 验证 tag
            fm, _ = parse_skill_md(content)
            tags = fm["metadata"]["hermes"]["tags"]
            self.assertIn("imported", tags)
            self.assertIn("org", tags)

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_with_skill_path_and_name_override(self, mock_fetch_raw, mock_fetch_list):
        """使用自定义 skill_path 并且 name 覆盖"""
        mock_fetch_list.return_value = [
            {"path": "custom/path/react-best-practices/SKILL.md", "type": "file"},
        ]
        mock_fetch_raw.return_value = """\
---
name: react-best-practices
description: React best practices
---
# Original name: react-best-practices
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "vercel-labs/agent-skills",
                "vercel-react-best-practices",  # Name override
                skill_path="custom/path/react-best-practices",
                category="software-development",
                target_dir=tmpdir,
            )
            self.assertTrue(result["success"])
            with open(result["path"], "r") as f:
                content = f.read()
            fm, _ = parse_skill_md(content)
            # Name should be overridden
            self.assertEqual(fm["name"], "vercel-react-best-practices")

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_uses_custom_skill_path(self, mock_fetch_raw, mock_fetch_list):
        """验证 skill_path 被传递给 _fetch_skill_list"""
        mock_fetch_list.return_value = [
            {"path": "skills/react-best-practices/SKILL.md", "type": "file"},
        ]
        mock_fetch_raw.return_value = "---\nname: test\ndescription: test\n---\nbody"

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "org/repo", "test-skill",
                skill_path="skills/react-best-practices",
                target_dir=tmpdir,
            )
            self.assertTrue(result["success"])
            # Verify the skill path was used in _fetch_skill_list call
            mock_fetch_list.assert_called_with("org", "repo", "skills/react-best-practices")

    @patch("bridge._fetch_skill_list")
    def test_skill_not_found(self, mock_fetch_list):
        mock_fetch_list.side_effect = RuntimeError("找不到 skill")
        result = _import_single_skill("org/repo", "nonexistent")
        self.assertFalse(result["success"])

    @patch("bridge._fetch_skill_list")
    def test_invalid_repo_format(self, mock_fetch_list):
        result = _import_single_skill("invalid", "test")
        self.assertFalse(result["success"])
        self.assertTrue(any("owner/repo" in e for e in result["errors"]))

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_invalid_frontmatter(self, mock_fetch_raw, mock_fetch_list):
        mock_fetch_list.return_value = [
            {"path": "skills/bad-skill/SKILL.md", "type": "file"},
        ]
        mock_fetch_raw.return_value = "This is just text without frontmatter"

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "org/repo", "bad-skill", target_dir=tmpdir
            )
            self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
