#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from batch_commit import apply as _apply
from batch_commit.apply import (
    apply_commit_to_worktree,
    commit_allowed_paths,
    commit_hunk_paths,
    describe_commit,
    ensure_hook_result_is_absorbable,
    restore_index,
    run_pre_commit_hook,
    shadow_worktree,
    sync_worktree_paths,
)
from batch_commit.config import (
    deep_merge_config,
    enforce_local_config_gate,
    load_fex_skills_config,
    load_optional_config_file,
    load_skills_lock,
    resolve_config_context,
    resolve_emoji_commit_language,
)
from batch_commit.constants import (
    AGENT_SKILLS_PREFIX,
    BREAKING_CHANGE_PATTERN,
    DEFAULT_EMOJI_COMMIT_LANGUAGE,
    FEX_SKILLS_CONFIG_PATH,
    FEX_SKILLS_LOCAL_CONFIG_PATH,
    FORBIDDEN_COAUTHOR_PATTERN,
    HEADER_PATTERN,
    HUNK_HEADER_PATTERN,
    JIRA_KEY_PATTERN,
    JIRA_REFS_PATTERN,
    JIRA_URL_PATTERN,
    REPO_SKILL_PACKAGES_GROUP,
    SKILLS_LOCK_PATH,
    SUPPORTED_EMOJI_COMMIT_LANGUAGES,
    TRAILER_PATTERN,
)
from batch_commit.diff_parser import (
    build_untracked_patch_blocks,
    change_type_summary,
    detect_change_type,
    diff_is_whitespace_only,
    parse_diff_git_paths,
    parse_file_patch,
    parse_hunk_header,
    split_patch_blocks,
    stable_id,
    trim_path_label,
)
from batch_commit.errors import BatchPlanError
from batch_commit.git_utils import (
    index_entries,
    list_git_paths,
    path_is_ignored,
    path_is_tracked,
    resolve_repo_root,
    run_git,
    split_nul_paths,
    staged_paths,
    unstaged_paths,
    untracked_paths,
)
from batch_commit.inventory import (
    annotate_agent_skill_file,
    build_inventory,
    parse_agent_skill_path,
    parse_skill_frontmatter_name,
    skill_lock_has_source,
    symlink_points_to_source,
)
from batch_commit.message import (
    build_commit_message,
    extract_jira_keys,
    normalize_body_item,
    normalize_jira_refs,
    resolve_agent_name,
    sanitize_agent_name,
    validate_commit_message_text,
)
from batch_commit.plan import load_json_file, validate_plan
from batch_commit.preview import (
    build_preview_text,
    build_skill_snapshot_preview,
    preview_language,
    skill_snapshot_suggested_header,
)


def _with_facade_git(func, *args: Any, **kwargs: Any):
    """Run apply helpers with the facade-level run_git for test patch compatibility.

    Example:
        _with_facade_git(_apply.apply_commits_transaction, repo_path, start, final)
    """
    original_run_git = _apply.run_git
    _apply.run_git = run_git
    try:
        return func(*args, **kwargs)
    finally:
        _apply.run_git = original_run_git


def create_commits_with_temp_index(repo_path, validation):
    """Compatibility wrapper for batch_commit.apply.create_commits_with_temp_index.

    Example:
        start_head, final_commit, commits = create_commits_with_temp_index(
            repo_path,
            validation,
        )
    """
    return _with_facade_git(_apply.create_commits_with_temp_index, repo_path, validation)


def apply_commits_transaction(
    repo_path,
    start_head,
    final_commit,
    *,
    worktree_paths=None,
):
    """Compatibility wrapper for batch_commit.apply.apply_commits_transaction.

    Example:
        apply_commits_transaction(repo_path, start_head, final_commit)
    """
    return _with_facade_git(
        _apply.apply_commits_transaction,
        repo_path,
        start_head,
        final_commit,
        worktree_paths=worktree_paths,
    )


def cmd_inventory(args: argparse.Namespace) -> None:
    """CLI 子命令：输出当前 inventory JSON。

    Example:
        python3 commit_batches.py inventory --repo /path/to/repo
    """
    config_context = resolve_config_context(args.repo)
    inventory = build_inventory(config_context["repo_root"], args.base, args.scope)
    inventory["config"] = {
        "emoji_commit_language": config_context["language"],
        "warnings": config_context["warnings"],
    }
    print(json.dumps(inventory, ensure_ascii=False, indent=2))


def cmd_preview_plan(args: argparse.Namespace) -> None:
    """CLI 子命令：校验计划并输出预览文本。

    Example:
        python3 commit_batches.py preview-plan --repo /path/to/repo --plan plan.json
    """
    config_context = resolve_config_context(args.repo)
    for warning in config_context["warnings"]:
        print(warning, file=sys.stderr)
    plan = load_json_file(args.plan)
    validation = validate_plan(config_context["repo_root"], plan)
    validation["config"] = {
        "emoji_commit_language": config_context["language"],
        "warnings": config_context["warnings"],
    }
    sys.stdout.write(build_preview_text(validation))


def cmd_apply_plan(args: argparse.Namespace) -> None:
    """CLI 子命令：校验计划并事务式应用整组 commit。

    Example:
        python3 commit_batches.py apply-plan --repo /path/to/repo --plan plan.json
    """
    config_context = resolve_config_context(args.repo)
    for warning in config_context["warnings"]:
        print(warning, file=sys.stderr)
    plan = load_json_file(args.plan)
    validation = validate_plan(config_context["repo_root"], plan)
    start_head, final_commit, created_commits = create_commits_with_temp_index(
        config_context["repo_root"],
        validation,
    )
    worktree_paths = None
    if validation["input_scope"] == "worktree":
        worktree_paths = {
            path
            for commit in validation["commits"]
            for path in commit_allowed_paths(validation, commit)
        }
    apply_commits_transaction(
        config_context["repo_root"],
        start_head,
        final_commit,
        worktree_paths=worktree_paths,
    )
    print(
        json.dumps(
            {
                "base_head": start_head,
                "final_head": final_commit,
                "created_commits": created_commits,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    """构建 `inventory / preview-plan / apply-plan` 三个 CLI 入口。

    Example:
        parser = build_parser()
        args = parser.parse_args(["inventory"])
    """
    def add_repo_argument(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--repo",
            default=argparse.SUPPRESS,
            help="Git repository path",
        )

    parser = argparse.ArgumentParser(
        description="Split staged or worktree changes into previewable emoji-commit batches."
    )
    add_repo_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser(
        "inventory",
        help="Output the current change inventory as JSON",
    )
    add_repo_argument(inventory_parser)
    inventory_parser.add_argument(
        "--base",
        default="HEAD",
        help="Base ref for inventory generation",
    )
    inventory_parser.add_argument(
        "--scope",
        choices=("worktree", "staged"),
        default="worktree",
        help="Inventory scope: full worktree or staged-only",
    )
    inventory_parser.set_defaults(func=cmd_inventory)

    preview_parser = subparsers.add_parser(
        "preview-plan",
        help="Render a human-readable preview for a batch plan",
    )
    add_repo_argument(preview_parser)
    preview_parser.add_argument("--plan", required=True, help="Path to the plan JSON file")
    preview_parser.set_defaults(func=cmd_preview_plan)

    apply_parser = subparsers.add_parser(
        "apply-plan",
        help="Apply a confirmed batch plan transactionally",
    )
    add_repo_argument(apply_parser)
    apply_parser.add_argument("--plan", required=True, help="Path to the plan JSON file")
    apply_parser.set_defaults(func=cmd_apply_plan)

    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行主入口，统一处理 BatchPlanError 的退出码。

    Example:
        raise SystemExit(main(["inventory", "--repo", "."]))
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "repo"):
        args.repo = "."
    try:
        args.func(args)
    except BatchPlanError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
