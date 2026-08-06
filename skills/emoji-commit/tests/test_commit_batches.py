import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import commit_batches  # noqa: E402


class CommitBatchesTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")

    def tearDown(self):
        self.tempdir.cleanup()

    def git(self, *args, input_text=None, check=True):
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            input=input_text,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(
                f"git {' '.join(args)} failed\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "commit_batches.py"), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(
                f"cli {' '.join(args)} failed\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def write_text(self, relative_path, content):
        target = self.repo / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def write_bytes(self, relative_path, content):
        target = self.repo / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def commit_all(self, message="init"):
        self.git("add", "-A")
        self.git("commit", "-m", message)

    def write_pre_commit_hook(self, content):
        hooks_path = Path(self.git("rev-parse", "--git-path", "hooks").stdout.strip())
        if not hooks_path.is_absolute():
            hooks_path = self.repo / hooks_path
        hooks_path.mkdir(parents=True, exist_ok=True)
        hook_path = hooks_path / "pre-commit"
        hook_path.write_text(content, encoding="utf-8")
        hook_path.chmod(0o755)
        return hook_path

    def build_plan(self, inventory, commits):
        return {
            "base_head": inventory["base_head"],
            "input_scope": inventory["input_scope"],
            "commits": commits,
        }

    def test_load_fex_skills_config_defaults_when_missing(self):
        config, warnings, repo_root = commit_batches.load_fex_skills_config(self.repo)
        language, language_warnings = commit_batches.resolve_emoji_commit_language(config)

        self.assertEqual(repo_root.resolve(), self.repo.resolve())
        self.assertEqual(config, {})
        self.assertEqual(warnings, [])
        self.assertEqual(language, "en")
        self.assertEqual(language_warnings, [])

    def test_load_fex_skills_config_reads_project_config(self):
        self.write_text(
            ".agents/fex-skills.config.json",
            json.dumps({"emoji-commit": {"language": "zh"}}, ensure_ascii=False),
        )

        config, warnings, _ = commit_batches.load_fex_skills_config(self.repo)
        language, language_warnings = commit_batches.resolve_emoji_commit_language(config)

        self.assertEqual(config["emoji-commit"]["language"], "zh")
        self.assertEqual(warnings, [])
        self.assertEqual(language, "zh")
        self.assertEqual(language_warnings, [])

    def test_load_fex_skills_config_merges_local_over_project(self):
        self.write_text(
            ".agents/fex-skills.config.json",
            json.dumps(
                {
                    "emoji-commit": {
                        "language": "en",
                        "preview": {
                            "showReason": True,
                            "showFiles": True,
                        },
                    }
                },
                ensure_ascii=False,
            ),
        )
        self.write_text(
            ".agents/fex-skills.config.local.json",
            json.dumps(
                {
                    "emoji-commit": {
                        "language": "zh",
                        "preview": {
                            "showFiles": False,
                        },
                    }
                },
                ensure_ascii=False,
            ),
        )

        config, warnings, _ = commit_batches.load_fex_skills_config(self.repo)

        self.assertEqual(warnings, [])
        self.assertEqual(
            config,
            {
                "emoji-commit": {
                    "language": "zh",
                    "preview": {
                        "showReason": True,
                        "showFiles": False,
                    },
                }
            },
        )

    def test_load_fex_skills_config_local_conflicting_value_overrides_project(self):
        self.write_text(
            ".agents/fex-skills.config.json",
            json.dumps({"emoji-commit": {"language": "en"}}, ensure_ascii=False),
        )
        self.write_text(
            ".agents/fex-skills.config.local.json",
            json.dumps({"emoji-commit": "invalid shape"}, ensure_ascii=False),
        )

        config, warnings, _ = commit_batches.load_fex_skills_config(self.repo)
        language, language_warnings = commit_batches.resolve_emoji_commit_language(config)

        self.assertEqual(warnings, [])
        self.assertEqual(config["emoji-commit"], "invalid shape")
        self.assertEqual(language, "en")
        self.assertIn("emoji-commit config must be an object", language_warnings[0])

    def test_resolve_emoji_commit_language_rejects_unsupported_value(self):
        language, warnings = commit_batches.resolve_emoji_commit_language(
            {"emoji-commit": {"language": "jp"}}
        )

        self.assertEqual(language, "en")
        self.assertIn('"jp" is unsupported', warnings[0])

    def test_local_config_gate_blocks_unignored_local_config(self):
        self.write_text(
            ".agents/fex-skills.config.local.json",
            json.dumps({"emoji-commit": {"language": "zh"}}, ensure_ascii=False),
        )

        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "local-only; add it to .gitignore",
        ):
            commit_batches.enforce_local_config_gate(self.repo)

    def test_local_config_gate_passes_when_ignored_and_untracked(self):
        self.write_text(".gitignore", ".agents/fex-skills.config.local.json\n")
        self.write_text(
            ".agents/fex-skills.config.local.json",
            json.dumps({"emoji-commit": {"language": "zh"}}, ensure_ascii=False),
        )

        self.assertEqual(
            commit_batches.enforce_local_config_gate(self.repo).resolve(),
            self.repo.resolve(),
        )

    def test_local_config_gate_blocks_tracked_local_config_even_when_ignored(self):
        self.write_text(
            ".agents/fex-skills.config.local.json",
            json.dumps({"emoji-commit": {"language": "zh"}}, ensure_ascii=False),
        )
        self.git("add", ".agents/fex-skills.config.local.json")
        self.write_text(".gitignore", ".agents/fex-skills.config.local.json\n")

        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "tracked by Git",
        ):
            commit_batches.enforce_local_config_gate(self.repo)

    def test_inventory_includes_worktree_change_types_and_untracked(self):
        self.write_text("modify.txt", "base\n")
        self.write_text("delete.txt", "delete me\n")
        self.write_text("rename.txt", "rename me\n")
        self.write_bytes("binary.bin", b"\x00\x01\x02base")
        self.commit_all()

        self.write_text("modify.txt", "base changed\n")
        (self.repo / "delete.txt").unlink()
        self.git("mv", "rename.txt", "renamed.txt")
        self.write_bytes("binary.bin", b"\x00\x01\x02changed")
        self.git("add", "binary.bin", "renamed.txt")
        self.write_text("added.txt", "new file\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        files = {item["path"]: item for item in inventory["files"]}

        self.assertEqual(inventory["input_scope"], "worktree")
        self.assertEqual(inventory["stats"]["file_count"], 5)
        self.assertEqual(files["modify.txt"]["change_type"], "M")
        self.assertEqual(files["delete.txt"]["change_type"], "D")
        self.assertEqual(files["renamed.txt"]["change_type"], "R")
        self.assertEqual(files["renamed.txt"]["old_path"], "rename.txt")
        self.assertEqual(files["renamed.txt"]["new_path"], "renamed.txt")
        self.assertEqual(files["added.txt"]["change_type"], "A")
        self.assertTrue(files["binary.bin"]["binary"])

    def test_inventory_worktree_includes_staged_file_untracked_file_and_symlink(self):
        self.write_text("tracked.txt", "base\n")
        self.write_text("tracked-dir/seed.txt", "seed\n")
        self.commit_all()

        self.write_text("tracked.txt", "base changed\n")
        self.git("add", "tracked.txt")
        self.write_text("loose.txt", "new file\n")
        (self.repo / "tracked-dir-link").symlink_to("tracked-dir", target_is_directory=True)

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        files = {item["path"]: item for item in inventory["files"]}
        symlink_unit = next(item for item in inventory["units"] if item["path"] == "tracked-dir-link")

        self.assertEqual(inventory["stats"]["file_count"], 3)
        self.assertEqual(set(files), {"tracked.txt", "loose.txt", "tracked-dir-link"})
        self.assertEqual(files["tracked.txt"]["change_type"], "M")
        self.assertEqual(files["loose.txt"]["change_type"], "A")
        self.assertEqual(files["tracked-dir-link"]["change_type"], "A")
        self.assertEqual(symlink_unit["kind"], "file")

    def test_inventory_marks_lock_managed_agent_skill_snapshot(self):
        self.write_text(
            "skills-lock.json",
            json.dumps(
                {
                    "version": 1,
                    "skills": {
                        "code-style": {
                            "sourceUrl": "https://example.com/skills.git",
                            "sourceType": "git",
                            "skillPath": "skills/code-style/SKILL.md",
                            "computedHash": "abc123",
                        }
                    },
                }
            ),
        )
        self.write_text(
            ".agents/skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n",
        )
        self.commit_all()
        self.write_text(
            ".agents/skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n\nUpdated.\n",
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        skill_file = inventory["files"][0]

        self.assertEqual(skill_file["domain"], "agent-skill")
        self.assertEqual(skill_file["skill_name"], "code-style")
        self.assertEqual(skill_file["skill_origin"], "external-lock-managed")
        self.assertEqual(skill_file["recommended_group"], "repo-skill-packages")

    def test_inventory_marks_source_symlink_without_snapshot_group(self):
        self.write_text(
            "skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n",
        )
        self.commit_all()
        target = self.repo / ".agents" / "skills" / "code-style"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to("../../skills/code-style", target_is_directory=True)

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        skill_file = inventory["files"][0]

        self.assertEqual(skill_file["path"], ".agents/skills/code-style")
        self.assertEqual(skill_file["domain"], "agent-skill")
        self.assertEqual(skill_file["skill_origin"], "source-symlink")
        self.assertNotIn("recommended_group", skill_file)

    def test_preview_recommends_splitting_skill_snapshot_from_business_changes(self):
        self.write_text(
            ".agents/skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n",
        )
        self.write_text("app.txt", "base\n")
        self.commit_all()
        self.write_text(
            ".agents/skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n\nUpdated.\n",
        )
        self.write_text("app.txt", "changed\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        units_by_path = {unit["path"]: unit["id"] for unit in inventory["units"]}
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "app",
                    "reason": "commit the app change",
                    "split_mode": "file",
                    "units": [units_by_path["app.txt"]],
                    "message": {
                        "header": ":wrench: (app) update app text",
                        "body": [],
                    },
                },
                {
                    "id": "skills",
                    "reason": "commit the repo skill package snapshot",
                    "split_mode": "file",
                    "units": [units_by_path[".agents/skills/code-style/SKILL.md"]],
                    "message": {
                        "header": ":sparkles: (skills) update repo skill packages",
                        "body": [],
                    },
                },
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        preview = commit_batches.build_preview_text(validation)

        self.assertIn("Repo skill package snapshot detected:", preview)
        self.assertIn(":sparkles: (skills) update repo skill packages", preview)
        self.assertIn("Suggested split:", preview)
        self.assertIn("- code-style: repo-installed-skill", preview)
        self.assertIn("1. :wrench: (app) update app text", preview)

    def test_preview_uses_chinese_skill_snapshot_header_when_configured(self):
        self.write_text(
            ".agents/skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n",
        )
        self.commit_all()
        self.write_text(
            ".agents/skills/code-style/SKILL.md",
            "---\nname: code-style\n---\n\n# Code Style\n\nUpdated.\n",
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "skills",
                    "reason": "commit the repo skill package snapshot",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":sparkles: (skills) 更新项目技能",
                        "body": [],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        validation["config"] = {"emoji_commit_language": "zh", "warnings": []}
        preview = commit_batches.build_preview_text(validation)

        self.assertIn("Suggested grouping: :sparkles: (skills) 更新项目技能", preview)

    def test_preview_marks_skill_snapshot_noise_and_suspicious_metadata(self):
        self.write_text(
            "skills-lock.json",
            json.dumps(
                {
                    "version": 1,
                    "skills": {
                        "skill-creator": {
                            "sourceUrl": "https://github.com/anthropics/skills.git",
                            "sourceType": "github",
                        },
                        "drift": {
                            "sourceUrl": "https://example.com/skills.git",
                            "sourceType": "git",
                        },
                    },
                }
            ),
        )
        self.write_text(
            ".agents/skills/skill-creator/SKILL.md",
            "---\nname: wrong-name\n---\n\n# Skill Creator\ncontent\n",
        )
        self.write_text(".agents/skills/drift/README.md", "base\n")
        self.commit_all()
        self.write_text(
            ".agents/skills/skill-creator/SKILL.md",
            "---\nname: wrong-name\n---\n\n# Skill Creator\ncontent  \n",
        )
        self.write_text(".agents/skills/drift/README.md", "updated\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "skills",
                    "reason": "commit the repo skill package snapshot",
                    "split_mode": "file",
                    "units": [unit["id"] for unit in inventory["units"]],
                    "message": {
                        "header": ":sparkles: (skills) update repo skill packages",
                        "body": [],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        preview = commit_batches.build_preview_text(validation)

        self.assertIn("Suspicious/noise:", preview)
        self.assertIn("whitespace-only", preview)
        self.assertIn("suspicious-frontmatter", preview)
        self.assertIn("suspicious-lock-drift", preview)

    def test_non_overlapping_hunks_can_be_split_and_previewed(self):
        self.write_text("app.txt", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")
        self.commit_all()

        self.write_text("app.txt", "1x\n2\n3\n4\n5\n6\n7\n8\n9\n10x\n")
        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        app_file = inventory["files"][0]

        self.assertTrue(app_file["partial_split_supported"])
        self.assertEqual(len(app_file["unit_ids"]), 2)

        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "first",
                    "reason": "split the first hunk",
                    "split_mode": "hunk",
                    "units": [app_file["unit_ids"][0]],
                    "message": {
                        "header": ":wrench: (emoji-commit) capture the first hunk",
                        "body": ["take the first isolated edit"],
                    },
                },
                {
                    "id": "second",
                    "reason": "split the second hunk",
                    "split_mode": "hunk",
                    "units": [app_file["unit_ids"][1]],
                    "message": {
                        "header": ":wrench: (emoji-commit) capture the second hunk",
                        "body": ["take the second isolated edit"],
                    },
                },
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        preview = commit_batches.build_preview_text(validation)

        self.assertIn("emoji-commit batch preview", preview)
        self.assertIn("Input scope: worktree", preview)
        self.assertIn("Partial split: yes", preview)
        self.assertIn("capture the first hunk", preview)
        self.assertIn("app.txt @@ -1,4 +1,4 @@", preview)
        self.assertIn("@@ -1,4 +1,4 @@", preview)

    def test_build_commit_message_normalizes_body_and_trailer(self):
        message = commit_batches.build_commit_message(
            {
                "header": ":wrench: (emoji-commit) normalize batched commit text",
                "body": ["  first item  ", "- second item"],
            }
        )

        self.assertIn("- first item\n- second item\n", message)
        self.assertEqual(message.count("AI-Co-Authored-By:"), 1)
        commit_batches.validate_commit_message_text(message)

    def test_build_commit_message_supports_no_scope_and_breaking_footer(self):
        message = commit_batches.build_commit_message(
            {
                "header": ":bug: ! reject duplicate units",
                "body": ["reject duplicate assignment earlier"],
                "breaking_change": "duplicate unit assignments are now rejected earlier",
            }
        )

        self.assertIn(":bug: ! reject duplicate units\n", message)
        self.assertIn(
            "BREAKING CHANGE: duplicate unit assignments are now rejected earlier\n\n",
            message,
        )
        self.assertRegex(message.rstrip().splitlines()[-1], r"^AI-Co-Authored-By: .+$")
        commit_batches.validate_commit_message_text(message)

    def test_build_commit_message_supports_jira_refs_without_breaking_footer(self):
        message = commit_batches.build_commit_message(
            {
                "header": ":memo: (emoji-commit) document jira refs footer behavior",
                "body": ["explain footer ordering with jira refs"],
                "jira_refs": [
                    "https://jira.meitu.com/browse/INTERNAL-1901",
                    "DATA-6755",
                ],
            }
        )

        self.assertIn(
            "Jira-Refs: INTERNAL-1901, DATA-6755\n\nAI-Co-Authored-By:",
            message,
        )
        commit_batches.validate_commit_message_text(message)

    def test_build_commit_message_supports_jira_refs_with_breaking_footer(self):
        message = commit_batches.build_commit_message(
            {
                "header": ":sparkles: (emoji-commit) ! add jira refs footer support",
                "body": ["support jira refs in commit footer"],
                "jira_refs": ["DATA-6755", "TECHPUB-19087"],
                "breaking_change": "footer parsing now recognizes jira refs",
            }
        )

        self.assertIn(
            "Jira-Refs: DATA-6755, TECHPUB-19087\n\n"
            "BREAKING CHANGE: footer parsing now recognizes jira refs\n\n",
            message,
        )
        commit_batches.validate_commit_message_text(message)

    def test_build_commit_message_rejects_more_than_five_body_items(self):
        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "commit body may include at most 5 items",
        ):
            commit_batches.build_commit_message(
                {
                    "header": ":memo: (emoji-commit) keep body output compact",
                    "body": [
                        "item 1",
                        "item 2",
                        "item 3",
                        "item 4",
                        "item 5",
                        "item 6",
                    ],
                }
            )

    def test_validate_commit_message_accepts_optional_scope(self):
        commit_batches.validate_commit_message_text(
            ":memo: document breaking footer behavior\n\nAI-Co-Authored-By: AI Agent\n"
        )
        commit_batches.validate_commit_message_text(
            ":sparkles: (emoji-commit) ! change header grammar\n\n"
            "BREAKING CHANGE: commit headers no longer require a scope\n\n"
            "AI-Co-Authored-By: AI Agent\n"
        )
        commit_batches.validate_commit_message_text(
            ":memo: (emoji-commit) document jira refs footer behavior\n\n"
            "Jira-Refs: INTERNAL-1901, DATA-6755\n\n"
            "AI-Co-Authored-By: AI Agent\n"
        )
        commit_batches.validate_commit_message_text(
            ":sparkles: (emoji-commit) ! add jira refs footer support\n\n"
            "Jira-Refs: DATA-6755, TECHPUB-19087\n\n"
            "BREAKING CHANGE: footer parsing now recognizes jira refs\n\n"
            "AI-Co-Authored-By: AI Agent\n"
        )

    def test_validate_commit_message_accepts_chinese_descriptions_with_english_footers(self):
        message = (
            ":sparkles: (emoji-commit) 支持中文提交描述\n\n"
            "- 读取 FEX skills 语言配置\n"
            "- 保持协议字段为英文\n\n"
            "Jira-Refs: DATA-6755\n\n"
            "BREAKING CHANGE: 默认语言配置会影响提交描述\n\n"
            "AI-Co-Authored-By: AI Agent\n"
        )

        commit_batches.validate_commit_message_text(message)

    def test_validate_commit_message_rejects_breaking_footer_out_of_order(self):
        message = (
            ":bug: ! reject duplicate units\n\n"
            "BREAKING CHANGE: duplicate unit assignments are now rejected earlier\n"
            "AI-Co-Authored-By: AI Agent\n"
        )

        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "BREAKING CHANGE footer must be separated from the AI-Co-Authored-By trailer by a blank line",
        ):
            commit_batches.validate_commit_message_text(message)

    def test_validate_commit_message_rejects_missing_blank_line_after_breaking_footer(self):
        message = (
            ":bug: ! reject duplicate units\n\n"
            "BREAKING CHANGE: duplicate unit assignments are now rejected earlier\n"
            "AI-Co-Authored-By: AI Agent\n"
        )

        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "BREAKING CHANGE footer must be separated from the AI-Co-Authored-By trailer by a blank line",
        ):
            commit_batches.validate_commit_message_text(message)

    def test_validate_commit_message_rejects_jira_refs_without_blank_line_before_breaking(self):
        message = (
            ":sparkles: (emoji-commit) ! add jira refs footer support\n\n"
            "Jira-Refs: DATA-6755, TECHPUB-19087\n"
            "BREAKING CHANGE: footer parsing now recognizes jira refs\n\n"
            "AI-Co-Authored-By: AI Agent\n"
        )

        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "Jira-Refs footer must be separated from BREAKING CHANGE by a blank line",
        ):
            commit_batches.validate_commit_message_text(message)

    def test_extract_jira_keys_deduplicates_and_preserves_order(self):
        jira_keys = commit_batches.extract_jira_keys(
            [
                "修复了 https://jira.meitu.com/browse/DATA-6755 https://jira.meitu.com/browse/TECHPUB-19087 这两个单子",
                "再补一个 DATA-6755 和 INTERNAL-1901",
            ]
        )

        self.assertEqual(jira_keys, ["DATA-6755", "TECHPUB-19087", "INTERNAL-1901"])

    def test_validate_plan_rejects_duplicate_unit_assignment(self):
        self.write_text("app.txt", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")
        self.commit_all()
        self.write_text("app.txt", "1x\n2\n3\n4\n5\n6\n7\n8\n9\n10x\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        unit_ids = inventory["files"][0]["unit_ids"]
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "first",
                    "reason": "take one hunk",
                    "split_mode": "hunk",
                    "units": [unit_ids[0]],
                    "message": {
                        "header": ":wrench: (emoji-commit) first hunk",
                        "body": [],
                    },
                },
                {
                    "id": "second",
                    "reason": "accidentally reuse a unit",
                    "split_mode": "hunk",
                    "units": [unit_ids[0], unit_ids[1]],
                    "message": {
                        "header": ":wrench: (emoji-commit) duplicate unit",
                        "body": [],
                    },
                },
            ],
        )

        with self.assertRaisesRegex(commit_batches.BatchPlanError, "assigned more than once"):
            commit_batches.validate_plan(self.repo, plan)

    def test_validate_plan_rejects_partial_file_coverage_for_file_mode(self):
        self.write_text("app.txt", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")
        self.commit_all()
        self.write_text("app.txt", "1x\n2\n3\n4\n5\n6\n7\n8\n9\n10x\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        unit_ids = inventory["files"][0]["unit_ids"]
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "first",
                    "reason": "incorrectly claim a whole-file split",
                    "split_mode": "file",
                    "units": [unit_ids[0]],
                    "message": {
                        "header": ":wrench: (emoji-commit) misuse file split",
                        "body": [],
                    },
                },
                {
                    "id": "second",
                    "reason": "cover the remaining hunk",
                    "split_mode": "hunk",
                    "units": [unit_ids[1]],
                    "message": {
                        "header": ":wrench: (emoji-commit) remaining hunk",
                        "body": [],
                    },
                },
            ],
        )

        with self.assertRaisesRegex(commit_batches.BatchPlanError, "does not cover full file"):
            commit_batches.validate_plan(self.repo, plan)

    def test_validate_plan_rejects_binary_partial_split(self):
        self.write_bytes("binary.bin", b"\x00\x01\x02base")
        self.commit_all()
        self.write_bytes("binary.bin", b"\x00\x01\x02changed")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        unit_id = inventory["units"][0]["id"]
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "binary",
                    "reason": "try to split a binary patch by hunk",
                    "split_mode": "hunk",
                    "units": [unit_id],
                    "message": {
                        "header": ":wrench: (emoji-commit) reject binary hunk split",
                        "body": [],
                    },
                }
            ],
        )

        with self.assertRaisesRegex(commit_batches.BatchPlanError, "unsupported unit"):
            commit_batches.validate_plan(self.repo, plan)

    def test_cli_inventory_accepts_repo_before_and_after_subcommand(self):
        self.write_text("app.txt", "base\n")
        self.commit_all()
        self.write_text("app.txt", "base changed\n")

        before = self.run_cli("--repo", str(self.repo), "inventory", "--scope", "worktree")
        after = self.run_cli("inventory", "--repo", str(self.repo), "--scope", "worktree")

        before_inventory = json.loads(before.stdout)
        after_inventory = json.loads(after.stdout)

        self.assertEqual(before_inventory["input_scope"], "worktree")
        self.assertEqual(before_inventory["config"]["emoji_commit_language"], "en")
        self.assertEqual(before_inventory["stats"], after_inventory["stats"])
        self.assertEqual(before_inventory["files"], after_inventory["files"])

    def test_cli_preview_plan_accepts_repo_before_and_after_subcommand(self):
        self.write_text("app.txt", "one\ntwo\n")
        self.commit_all()
        self.write_text("app.txt", "one changed\ntwo\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "preview the only unit",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) preview one change",
                        "body": ["render a stable preview"],
                    },
                }
            ],
        )

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(plan, handle)
            plan_path = handle.name

        try:
            before = self.run_cli(
                "--repo",
                str(self.repo),
                "preview-plan",
                "--plan",
                plan_path,
            )
            after = self.run_cli(
                "preview-plan",
                "--repo",
                str(self.repo),
                "--plan",
                plan_path,
            )
        finally:
            Path(plan_path).unlink()

        self.assertIn("emoji-commit batch preview", before.stdout)
        self.assertEqual(before.stdout, after.stdout)

    def test_apply_plan_creates_multiple_commits_from_worktree(self):
        self.write_text("app.txt", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")
        self.commit_all()

        self.write_text("app.txt", "1x\n2\n3\n4\n5\n6\n7\n8\n9\n10x\n")
        self.write_text("new.txt", "fresh content\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        app_units = inventory["files"][0]["unit_ids"]
        new_unit = next(
            item["id"] for item in inventory["units"] if item["path"] == "new.txt"
        )

        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "first",
                    "reason": "commit the first isolated edit",
                    "split_mode": "hunk",
                    "units": [app_units[0]],
                    "message": {
                        "header": ":wrench: (emoji-commit) commit the first app hunk",
                        "body": ["capture the first edit in app.txt"],
                    },
                },
                {
                    "id": "second",
                    "reason": "commit the second isolated edit",
                    "split_mode": "hunk",
                    "units": [app_units[1]],
                    "message": {
                        "header": ":wrench: (emoji-commit) commit the second app hunk",
                        "body": ["capture the second edit in app.txt"],
                    },
                },
                {
                    "id": "third",
                    "reason": "commit the added file",
                    "split_mode": "file",
                    "units": [new_unit],
                    "message": {
                        "header": ":sparkles: (emoji-commit) add the new worktree file",
                        "body": ["include the untracked file in its own commit"],
                    },
                },
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        start_head, final_commit, created_commits = commit_batches.create_commits_with_temp_index(
            self.repo,
            validation,
        )
        commit_batches.apply_commits_transaction(self.repo, start_head, final_commit)

        self.assertEqual(len(created_commits), 3)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), final_commit)
        self.assertEqual(self.git("status", "--short").stdout.strip(), "")
        self.assertEqual(
            self.git("log", "--pretty=%s", "-3").stdout.strip().splitlines(),
            [
                ":sparkles: (emoji-commit) add the new worktree file",
                ":wrench: (emoji-commit) commit the second app hunk",
                ":wrench: (emoji-commit) commit the first app hunk",
            ],
        )

    def test_apply_plan_allows_missing_pre_commit_hook(self):
        self.write_text("app.txt", "base\n")
        self.commit_all()
        self.write_text("app.txt", "changed\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "apply without a hook",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) allow missing hook",
                        "body": ["keep batch apply working without hooks"],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        start_head, final_commit, _ = commit_batches.create_commits_with_temp_index(
            self.repo,
            validation,
        )
        commit_batches.apply_commits_transaction(self.repo, start_head, final_commit)

        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), final_commit)

    def test_apply_plan_runs_pre_commit_for_each_planned_commit(self):
        self.write_text("one.txt", "base one\n")
        self.write_text("two.txt", "base two\n")
        self.commit_all()
        self.write_text("one.txt", "changed one\n")
        self.write_text("two.txt", "changed two\n")
        hook_log = self.repo / "hook-runs.log"
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            f"git diff --cached --name-only >> {hook_log}\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        units_by_path = {unit["path"]: unit["id"] for unit in inventory["units"]}
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "one",
                    "reason": "apply first file",
                    "split_mode": "file",
                    "units": [units_by_path["one.txt"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) commit first file",
                        "body": [],
                    },
                },
                {
                    "id": "two",
                    "reason": "apply second file",
                    "split_mode": "file",
                    "units": [units_by_path["two.txt"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) commit second file",
                        "body": [],
                    },
                },
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        start_head, final_commit, _ = commit_batches.create_commits_with_temp_index(
            self.repo,
            validation,
        )
        commit_batches.apply_commits_transaction(self.repo, start_head, final_commit)

        self.assertEqual(
            hook_log.read_text(encoding="utf-8").splitlines(),
            ["one.txt", "two.txt"],
        )

    def test_apply_plan_pre_commit_failure_keeps_main_head_unchanged(self):
        self.write_text("app.txt", "base\n")
        self.commit_all()
        start_head = self.git("rev-parse", "HEAD").stdout.strip()
        self.write_text("app.txt", "changed\n")
        self.write_pre_commit_hook("#!/bin/sh\nexit 1\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "exercise hook failure",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) fail hook",
                        "body": [],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "pre-commit hook failed for single",
        ):
            commit_batches.create_commits_with_temp_index(self.repo, validation)

        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), start_head)

    def test_apply_plan_hook_reads_shadow_worktree_snapshot(self):
        self.write_text("one.txt", "base one\n")
        self.write_text("two.txt", "base two\n")
        self.commit_all()
        self.write_text("one.txt", "changed one\n")
        self.write_text("two.txt", "changed two\n")
        hook_log = self.repo / "hook-snapshots.log"
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            f"printf '%s|%s\\n' \"$(cat one.txt)\" \"$(cat two.txt)\" >> {hook_log}\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        units_by_path = {unit["path"]: unit["id"] for unit in inventory["units"]}
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "one",
                    "reason": "apply first file",
                    "split_mode": "file",
                    "units": [units_by_path["one.txt"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) commit one",
                        "body": [],
                    },
                },
                {
                    "id": "two",
                    "reason": "apply second file",
                    "split_mode": "file",
                    "units": [units_by_path["two.txt"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) commit two",
                        "body": [],
                    },
                },
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        start_head, final_commit, _ = commit_batches.create_commits_with_temp_index(
            self.repo,
            validation,
        )
        commit_batches.apply_commits_transaction(self.repo, start_head, final_commit)

        self.assertEqual(
            hook_log.read_text(encoding="utf-8").splitlines(),
            ["changed one|base two", "changed one|changed two"],
        )

    def test_apply_plan_absorbs_staged_hook_changes_inside_commit_boundary(self):
        self.write_text("app.txt", "base\n")
        self.commit_all()
        self.write_text("app.txt", "changed\n")
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            "printf 'changed by hook\\n' > app.txt\n"
            "git add app.txt\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "absorb formatter output",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) absorb hook changes",
                        "body": [],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        start_head, final_commit, _ = commit_batches.create_commits_with_temp_index(
            self.repo,
            validation,
        )
        commit_batches.apply_commits_transaction(self.repo, start_head, final_commit)

        self.assertEqual(
            self.git("show", "HEAD:app.txt").stdout,
            "changed by hook\n",
        )

    def test_cli_apply_plan_syncs_hook_absorbed_worktree_content(self):
        self.write_text("app.txt", "base\n")
        self.commit_all()
        self.write_text("app.txt", "changed\n")
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            "printf 'changed by hook\\n' > app.txt\n"
            "git add app.txt\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "sync formatter output",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) sync hook changes",
                        "body": [],
                    },
                }
            ],
        )

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(plan, handle)
            plan_path = handle.name

        try:
            self.run_cli("apply-plan", "--repo", str(self.repo), "--plan", plan_path)
        finally:
            Path(plan_path).unlink()

        self.assertEqual((self.repo / "app.txt").read_text(encoding="utf-8"), "changed by hook\n")
        self.assertEqual(self.git("status", "--short").stdout.strip(), "")

    def test_apply_plan_rejects_hook_changes_outside_commit_boundary(self):
        self.write_text("app.txt", "base app\n")
        self.write_text("other.txt", "base other\n")
        self.commit_all()
        self.write_text("app.txt", "changed app\n")
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            "printf 'changed outside\\n' > other.txt\n"
            "git add other.txt\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "reject outside hook changes",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) reject outside hook change",
                        "body": [],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "modified paths outside single",
        ):
            commit_batches.create_commits_with_temp_index(self.repo, validation)

    def test_apply_plan_rejects_unstaged_hook_changes(self):
        self.write_text("app.txt", "base\n")
        self.commit_all()
        self.write_text("app.txt", "changed\n")
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            "printf 'changed but not staged\\n' > app.txt\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "reject unstaged hook changes",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) reject unstaged hook change",
                        "body": [],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "left unstaged changes for single",
        ):
            commit_batches.create_commits_with_temp_index(self.repo, validation)

    def test_apply_plan_rejects_hunk_split_when_hook_modifies_same_file(self):
        self.write_text("app.txt", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")
        self.commit_all()
        self.write_text("app.txt", "1x\n2\n3\n4\n5\n6\n7\n8\n9\n10x\n")
        self.write_pre_commit_hook(
            "#!/bin/sh\n"
            "printf '\\n' >> app.txt\n"
            "git add app.txt\n"
        )

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        unit_id = inventory["files"][0]["unit_ids"][0]
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "first",
                    "reason": "reject hunk formatter conflict",
                    "split_mode": "hunk",
                    "units": [unit_id],
                    "message": {
                        "header": ":wrench: (emoji-commit) reject hunk hook change",
                        "body": [],
                    },
                },
                {
                    "id": "second",
                    "reason": "cover the remaining hunk",
                    "split_mode": "hunk",
                    "units": [inventory["files"][0]["unit_ids"][1]],
                    "message": {
                        "header": ":wrench: (emoji-commit) remaining hunk",
                        "body": [],
                    },
                },
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        with self.assertRaisesRegex(
            commit_batches.BatchPlanError,
            "modified hunk-split file for first",
        ):
            commit_batches.create_commits_with_temp_index(self.repo, validation)

    def test_validate_plan_rejects_head_drift(self):
        self.write_text("app.txt", "one\ntwo\n")
        self.commit_all()
        self.write_text("app.txt", "one changed\ntwo\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "take the only unit",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) apply one change",
                        "body": [],
                    },
                }
            ],
        )

        self.write_text("other.txt", "other\n")
        self.git("add", "other.txt")
        self.git("commit", "-m", "advance head")

        with self.assertRaisesRegex(commit_batches.BatchPlanError, "HEAD changed since preview"):
            commit_batches.validate_plan(self.repo, plan)

    def test_apply_plan_rolls_back_head_and_index_on_failure(self):
        self.write_text("app.txt", "one\ntwo\n")
        self.commit_all()
        self.write_text("app.txt", "one changed\ntwo\n")

        inventory = commit_batches.build_inventory(self.repo, "HEAD", "worktree")
        plan = self.build_plan(
            inventory,
            [
                {
                    "id": "single",
                    "reason": "apply the only unit",
                    "split_mode": "file",
                    "units": [inventory["units"][0]["id"]],
                    "message": {
                        "header": ":wrench: (emoji-commit) roll back on apply failure",
                        "body": ["exercise transactional rollback"],
                    },
                }
            ],
        )

        validation = commit_batches.validate_plan(self.repo, plan)
        start_head, final_commit, _ = commit_batches.create_commits_with_temp_index(
            self.repo,
            validation,
        )
        before_status = self.git("status", "--short").stdout
        real_run_git = commit_batches.run_git

        def flaky_run_git(repo_path, args, **kwargs):
            result = real_run_git(repo_path, args, **kwargs)
            if args == ["read-tree", final_commit]:
                raise commit_batches.BatchPlanError("forced read-tree failure")
            return result

        with mock.patch.object(commit_batches, "run_git", side_effect=flaky_run_git):
            with self.assertRaisesRegex(commit_batches.BatchPlanError, "forced read-tree failure"):
                commit_batches.apply_commits_transaction(self.repo, start_head, final_commit)

        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), start_head)
        self.assertEqual(self.git("status", "--short").stdout, before_status)


if __name__ == "__main__":
    unittest.main()
