"""
test_bridge.py — bridge.py 核心函数单元测试

覆盖 import、validate、batch-import 三个主要流程以及辅助函数。
使用 unittest.mock 模拟 GitHub API 和文件系统，不依赖网络。
"""

import argparse
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure we can import bridge.py from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bridge import (
    _fetch_raw_github,
    _fetch_skill_list,
    _import_single_skill,
    cmd_batch_import,
    cmd_import,
    cmd_list,
    cmd_validate,
    main,
)

# ─── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def sample_skill_md():
    """有效的 Vercel 格式 SKILL.md"""
    return """\
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


@pytest.fixture
def sample_skill_body():
    return "# React Best Practices\n\nThis is a comprehensive guide for React performance optimization.\n"


@pytest.fixture
def valid_skill_list():
    return [{"path": "skills/test-skill/SKILL.md", "type": "file"}]


@pytest.fixture
def temp_skills_dir():
    """创建临时目录模拟 ~/.hermes/skills"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ─── _fetch_raw_github ────────────────────────────────────────


class TestFetchRawGithub:
    """_fetch_raw_github — GitHub raw content 获取"""

    @patch("bridge.urllib.request.urlopen")
    def test_successful_fetch(self, mock_urlopen):
        """正常获取返回解码后的内容"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"name: test\ndescription: test\n"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = _fetch_raw_github("org", "repo", "skills/test/SKILL.md")
        assert result == "name: test\ndescription: test\n"

        # Verify URL was constructed correctly
        call_url = mock_urlopen.call_args[0][0].full_url
        assert "raw.githubusercontent.com/org/repo/main/skills/test/SKILL.md" in call_url

    @patch("bridge.urllib.request.urlopen")
    def test_404_triggers_master_fallback(self, mock_urlopen):
        """404 时自动尝试 master 分支"""
        # First call raises 404
        from urllib.error import HTTPError

        first_error = HTTPError(
            "http://example.com", 404, "Not Found", {}, None
        )
        # Second call succeeds
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fallback content"

        mock_urlopen.side_effect = [
            first_error,
            MagicMock(__enter__=MagicMock(return_value=mock_resp)),
        ]

        result = _fetch_raw_github("org", "repo", "skills/test/SKILL.md")
        assert result == "fallback content"
        assert mock_urlopen.call_count == 2

    @patch("bridge.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        """网络错误包装为 RuntimeError"""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(RuntimeError, match="无法从 GitHub 获取"):
            _fetch_raw_github("org", "repo", "skills/test/SKILL.md")


# ─── _fetch_skill_list ────────────────────────────────────────


class TestFetchSkillList:
    """_fetch_skill_list — skill 目录文件列表获取"""

    @patch("bridge._fetch_raw_github")
    def test_directory_path(self, mock_fetch):
        """目录路径自动尝试 SKILL.md（scripts 文件获取失败时只返回 SKILL.md）"""
        def side_effect(owner, repo, path):
            if path.endswith("SKILL.md"):
                return "content"
            raise RuntimeError("not found")

        mock_fetch.side_effect = side_effect

        result = _fetch_skill_list("org", "repo", "skills/test-skill")

        assert len(result) == 1
        assert result[0]["path"] == "skills/test-skill/SKILL.md"
        assert result[0]["type"] == "file"
        mock_fetch.assert_any_call("org", "repo", "skills/test-skill/SKILL.md")

    @patch("bridge._fetch_raw_github")
    def test_file_path_direct(self, mock_fetch):
        """.md 结尾的直接视为文件路径"""
        mock_fetch.return_value = "content"

        result = _fetch_skill_list("org", "repo", "skills/test-skill/SKILL.md")

        assert len(result) == 1
        assert result[0]["path"] == "skills/test-skill/SKILL.md"

    @patch("bridge._fetch_raw_github")
    def test_not_found(self, mock_fetch):
        """找不到 skill 时抛出 RuntimeError"""
        from urllib.error import HTTPError

        mock_fetch.side_effect = RuntimeError("not found")

        with pytest.raises(RuntimeError, match="找不到 skill"):
            _fetch_skill_list("org", "repo", "skills/nonexistent")

    @patch("bridge._fetch_raw_github")
    def test_with_script_files(self, mock_fetch):
        """找到 skill 后还会尝试获取 scripts 目录文件"""
        # SKILL.md succeeds, scripts also succeed for some
        def side_effect(owner, repo, path):
            if "SKILL.md" in path:
                return "content"
            if "scripts/requirements.txt" in path:
                return "requests==2.31.0"
            raise RuntimeError("not found")

        mock_fetch.side_effect = side_effect

        result = _fetch_skill_list("org", "repo", "skills/test-skill")

        paths = [f["path"] for f in result]
        assert "skills/test-skill/SKILL.md" in paths
        assert "skills/test-skill/scripts/requirements.txt" in paths
        assert "skills/test-skill/scripts/run.sh" not in paths  # not found


# ─── _import_single_skill ─────────────────────────────────────


class TestImportSingleSkill:
    """_import_single_skill — 单个 skill 导入"""

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_success(self, mock_fetch_raw, mock_fetch_list, sample_skill_md):
        """正常导入应成功并写入文件"""
        mock_fetch_list.return_value = [
            {"path": "skills/test-skill/SKILL.md", "type": "file"}
        ]
        mock_fetch_raw.return_value = sample_skill_md

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "org/test-repo",
                "test-skill",
                category="software-development",
                target_dir=tmpdir,
            )

            assert result["success"] is True
            assert os.path.exists(result["path"])

            # 验证写入内容格式正确
            with open(result["path"]) as f:
                content = f.read()
            assert content.startswith("---")
            assert "name: test-skill" in content
            assert "imported_from: org/test-repo" in content

            # 验证分类目录结构
            expected_dir = os.path.join(tmpdir, "software-development", "test-skill")
            assert os.path.isdir(expected_dir)

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_name_override(self, mock_fetch_raw, mock_fetch_list):
        """JSON 配置中的 name 覆盖原始 skill 名"""
        mock_fetch_list.return_value = [
            {"path": "skills/react-best-practices/SKILL.md", "type": "file"}
        ]
        mock_fetch_raw.return_value = """\
---
name: react-best-practices
description: React best practices
---
# Original
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "vercel-labs/agent-skills",
                "vercel-react-best-practices",
                skill_path="skills/react-best-practices",
                category="software-development",
                target_dir=tmpdir,
            )
            assert result["success"] is True
            with open(result["path"]) as f:
                content = f.read()
            assert "name: vercel-react-best-practices" in content
            assert "name: react-best-practices" not in content

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_with_scripts(self, mock_fetch_raw, mock_fetch_list):
        """导入时同步复制 scripts 目录"""
        mock_fetch_list.return_value = [
            {"path": "skills/test-skill/SKILL.md", "type": "file"},
            {"path": "skills/test-skill/scripts/setup.sh", "type": "file"},
            {"path": "skills/test-skill/scripts/requirements.txt", "type": "file"},
        ]
        mock_fetch_raw.side_effect = [
            "---\nname: test-skill\ndescription: test\n---\nbody",
            "#!/bin/bash\necho setup",
            "requests==2.31.0",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "org/repo", "test-skill", target_dir=tmpdir
            )
            assert result["success"] is True

            # 验证 scripts 已复制（bridge.py 中 rel_path 包含 scripts/ 前缀）
            scripts_dir = os.path.join(tmpdir, "imported", "test-skill", "scripts")
            assert os.path.isfile(os.path.join(scripts_dir, "scripts", "setup.sh"))
            assert os.path.isfile(os.path.join(scripts_dir, "scripts", "requirements.txt"))

    @patch("bridge._fetch_skill_list")
    def test_invalid_repo_format(self, mock_fetch_list):
        """无效的 repo 格式返回错误"""
        result = _import_single_skill("invalid", "test")
        assert result["success"] is False
        assert any("owner/repo" in e for e in result["errors"])

    @patch("bridge._fetch_skill_list")
    def test_skill_not_found(self, mock_fetch_list):
        """Skill 找不到返回错误"""
        mock_fetch_list.side_effect = RuntimeError("找不到 skill")
        result = _import_single_skill("org/repo", "nonexistent")
        assert result["success"] is False
        assert "找不到 skill" in result["errors"][0]

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_invalid_frontmatter(self, mock_fetch_raw, mock_fetch_list):
        """无效的 frontmatter 返回错误"""
        mock_fetch_list.return_value = [
            {"path": "skills/bad-skill/SKILL.md", "type": "file"}
        ]
        mock_fetch_raw.return_value = "This is just text without frontmatter"

        with tempfile.TemporaryDirectory() as tmpdir:
            result = _import_single_skill(
                "org/repo", "bad-skill", target_dir=tmpdir
            )
            assert result["success"] is False
            assert "frontmatter" in result["errors"][0].lower()

    @patch("bridge._fetch_skill_list")
    @patch("bridge._fetch_raw_github")
    def test_import_with_custom_path(self, mock_fetch_raw, mock_fetch_list):
        """验证 skill_path 参数传递给 _fetch_skill_list"""
        mock_fetch_list.return_value = [
            {"path": "custom/react/SKILL.md", "type": "file"}
        ]
        mock_fetch_raw.return_value = "---\nname: test\ndescription: test\n---\nbody"

        with tempfile.TemporaryDirectory() as tmpdir:
            _import_single_skill(
                "org/repo", "test-skill",
                skill_path="custom/react",
                target_dir=tmpdir,
            )
            mock_fetch_list.assert_called_with("org", "repo", "custom/react")


# ─── cmd_batch_import ─────────────────────────────────────────


class TestCmdBatchImport:
    """cmd_batch_import — 批量导入"""

    @patch("bridge._import_single_skill")
    def test_all_succeed(self, mock_import):
        """全部成功返回 0"""
        mock_import.return_value = {"success": True, "name": "test", "path": "/tmp/test", "warnings": [], "errors": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "skills": [
                    {"name": "skill-a", "repo": "org/a", "category": "dev"},
                    {"name": "skill-b", "repo": "org/b"},
                ]
            }, f)
            fname = f.name

        try:
            args = argparse.Namespace(json_file=fname)
            rc = cmd_batch_import(args)
            assert rc == 0
            assert mock_import.call_count == 2
        finally:
            os.unlink(fname)

    @patch("bridge._import_single_skill")
    def test_partial_failure(self, mock_import):
        """部分失败返回 1"""
        mock_import.side_effect = [
            {"success": True, "name": "skill-a", "path": "/tmp/a", "warnings": [], "errors": []},
            {"success": False, "name": "skill-b", "path": "", "warnings": [], "errors": ["not found"]},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "skills": [
                    {"name": "skill-a", "repo": "org/a"},
                    {"name": "skill-b", "repo": "org/b"},
                ]
            }, f)
            fname = f.name

        try:
            args = argparse.Namespace(json_file=fname)
            rc = cmd_batch_import(args)
            assert rc == 1
        finally:
            os.unlink(fname)

    def test_empty_skills_list(self):
        """空的 skills 列表返回 1"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"skills": []}, f)
            fname = f.name

        try:
            args = argparse.Namespace(json_file=fname)
            rc = cmd_batch_import(args)
            assert rc == 1
        finally:
            os.unlink(fname)

    def test_missing_skills_key(self):
        """配置中缺少 skills 键返回 1"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"other": "data"}, f)
            fname = f.name

        try:
            args = argparse.Namespace(json_file=fname)
            rc = cmd_batch_import(args)
            assert rc == 1
        finally:
            os.unlink(fname)


# ─── cmd_validate ─────────────────────────────────────────────


class TestCmdValidate:
    """cmd_validate — 验证 skill"""

    def test_skills_dir_not_exist(self):
        """~/.hermes/skills 不存在时返回 1"""
        with patch("bridge.HERMES_SKILLS_DIR", "/tmp/nonexistent_skills_dir_xyz"):
            args = argparse.Namespace(name="any-skill")
            rc = cmd_validate(args)
            assert rc == 1

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("builtins.open")
    def test_validate_pass(self, mock_open, mock_isfile, mock_isdir, mock_listdir):
        """有效 skill 返回 0"""
        mock_listdir.side_effect = [
            ["software-development"],  # categories
            ["test-skill"],  # skills in category
        ]
        mock_isfile.return_value = True
        mock_open.return_value.read.return_value = """\
---
name: test-skill
description: A valid test skill
---
Body content
"""
        with patch("bridge.HERMES_SKILLS_DIR", "/fake/skills"):
            args = argparse.Namespace(name="test-skill")
            rc = cmd_validate(args)
            assert rc == 0

    @patch("os.listdir")
    @patch("os.path.isdir")
    def test_skill_not_found(self, mock_isdir, mock_listdir):
        """找不到 skill 返回 1"""
        mock_listdir.return_value = ["software-development"]
        mock_isdir.return_value = True

        with patch("bridge.HERMES_SKILLS_DIR", "/fake/skills"):
            args = argparse.Namespace(name="nonexistent")
            rc = cmd_validate(args)
            assert rc == 1


# ─── cmd_import (argparse wrapper) ────────────────────────────


class TestCmdImport:
    """cmd_import — import 命令入口"""

    @patch("bridge._import_single_skill")
    def test_import_success(self, mock_import):
        """成功导入返回 0"""
        mock_import.return_value = {
            "success": True, "name": "test-skill",
            "path": "/tmp/test-skill/SKILL.md",
            "warnings": ["note: something"], "errors": [],
        }
        args = argparse.Namespace(
            owner_repo="org/repo", skill="test-skill",
            category="imported", path=None,
        )
        rc = cmd_import(args)
        assert rc == 0

    @patch("bridge._import_single_skill")
    def test_import_failure(self, mock_import):
        """导入失败返回 1"""
        mock_import.return_value = {
            "success": False, "name": "bad-skill",
            "path": "", "warnings": [], "errors": ["invalid repo format"],
        }
        args = argparse.Namespace(
            owner_repo="invalid", skill="bad-skill",
            category="imported", path=None,
        )
        rc = cmd_import(args)
        assert rc == 1


# ─── cmd_list ─────────────────────────────────────────────────


class TestCmdList:
    """cmd_list — 列出已导入 skills"""

    def test_no_skills(self):
        """无 skill 时返回 0"""
        with patch("bridge.HERMES_SKILLS_DIR", "/tmp/nonexistent_skills_dir_xyz"):
            args = argparse.Namespace()
            rc = cmd_list(args)
            assert rc == 0

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("builtins.open")
    def test_with_skills(self, mock_open, mock_isfile, mock_isdir, mock_listdir):
        """有 skill 时列出并返回 0"""
        mock_listdir.side_effect = [
            ["software-development"],  # categories
            ["test-skill", "another-skill"],  # skills
        ]
        mock_isdir.return_value = True
        mock_isfile.return_value = True
        mock_open.return_value.read.return_value = """\
---
name: test-skill
description: test
metadata:
  hermes:
    imported_from: org/repo
---
body
"""
        with patch("bridge.HERMES_SKILLS_DIR", "/fake/skills"):
            args = argparse.Namespace()
            rc = cmd_list(args)
            assert rc == 0


# ─── main (CLI entry) ─────────────────────────────────────────


class TestMain:
    """main() — CLI 入口"""

    @patch("argparse.ArgumentParser.parse_args")
    def test_no_command(self, mock_parse):
        """无子命令返回 1"""
        mock_parse.return_value = argparse.Namespace(command=None)
        rc = main()
        assert rc == 1

    @patch("bridge.cmd_import")
    @patch("argparse.ArgumentParser.parse_args")
    def test_import_command(self, mock_parse, mock_cmd):
        """import 子命令被正确分发"""
        mock_cmd.return_value = 0
        mock_parse.return_value = argparse.Namespace(command="import", func=mock_cmd)
        rc = main()
        assert rc == 0
        mock_cmd.assert_called_once()

    @patch("bridge.cmd_batch_import")
    @patch("argparse.ArgumentParser.parse_args")
    def test_batch_import_command(self, mock_parse, mock_cmd):
        """batch-import 子命令被正确分发"""
        mock_cmd.return_value = 0
        mock_parse.return_value = argparse.Namespace(
            command="batch-import", func=mock_cmd
        )
        rc = main()
        assert rc == 0
        mock_cmd.assert_called_once()

    @patch("bridge.cmd_list")
    @patch("argparse.ArgumentParser.parse_args")
    def test_list_command(self, mock_parse, mock_cmd):
        """list 子命令被正确分发"""
        mock_cmd.return_value = 0
        mock_parse.return_value = argparse.Namespace(command="list", func=mock_cmd)
        rc = main()
        assert rc == 0
        mock_cmd.assert_called_once()

    @patch("bridge.cmd_validate")
    @patch("argparse.ArgumentParser.parse_args")
    def test_validate_command(self, mock_parse, mock_cmd):
        """validate 子命令被正确分发"""
        mock_cmd.return_value = 0
        mock_parse.return_value = argparse.Namespace(command="validate", func=mock_cmd)
        rc = main()
        assert rc == 0
        mock_cmd.assert_called_once()
