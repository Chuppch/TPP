from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from batch_commit.errors import BatchPlanError
from batch_commit.git_utils import (
    index_entries,
    path_is_tracked,
    run_git,
    staged_paths,
    unstaged_paths,
    untracked_paths,
)
from batch_commit.message import validate_commit_message_text


def commit_allowed_paths(validation: dict[str, Any], commit: dict[str, Any]) -> set[str]:
    """返回当前计划 commit 允许触碰的路径边界。

    Example:
        allowed_paths = commit_allowed_paths(validation, validation["commits"][0])
    """
    paths: set[str] = set()
    for unit_id in commit["units"]:
        unit = validation["units_by_id"][unit_id]
        file_record = validation["files_by_path"][unit["path"]]
        for key in ("path", "old_path", "new_path"):
            value = str(file_record.get(key) or "").strip()
            if value and value != "/dev/null":
                paths.add(value)
    return paths



def commit_hunk_paths(validation: dict[str, Any], commit: dict[str, Any]) -> set[str]:
    """返回 hunk split commit 覆盖的文件路径。"""
    if commit["split_mode"] != "hunk":
        return set()
    return {
        validation["units_by_id"][unit_id]["path"]
        for unit_id in commit["units"]
    }



def describe_commit(commit: dict[str, Any]) -> str:
    """生成 hook 错误中使用的 commit 标签。"""
    return f"{commit['id']} ({commit['message']['header']})"



@contextmanager
def shadow_worktree(repo_path: str | Path, start_head: str):
    """创建并清理用于运行 hook 的隔离 worktree。"""
    with tempfile.TemporaryDirectory(prefix="emoji-commit-worktree-") as temp_dir:
        worktree_path = Path(temp_dir) / "worktree"
        try:
            run_git(
                repo_path,
                [
                    "worktree",
                    "add",
                    "--detach",
                    "--quiet",
                    str(worktree_path),
                    start_head,
                ],
            )
            yield worktree_path
        finally:
            try:
                run_git(repo_path, ["worktree", "remove", "--force", str(worktree_path)])
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)
                try:
                    run_git(repo_path, ["worktree", "prune"])
                except Exception:
                    pass



def apply_commit_to_worktree(
    repo_path: str | Path,
    validation: dict[str, Any],
    commit: dict[str, Any],
) -> None:
    """把当前计划 commit 的 patch 应用到真实工作区并 stage。

    Example:
        apply_commit_to_worktree(worktree_path, validation, commit)
    """
    for unit_id in commit["units"]:
        patch = validation["units_by_id"][unit_id]["patch"]
        run_git(
            repo_path,
            ["apply", "--binary", "--whitespace=nowarn", "-"],
            input_text=patch,
        )

    allowed_paths = sorted(commit_allowed_paths(validation, commit))
    run_git(repo_path, ["add", "--all", "--", *allowed_paths])



def run_pre_commit_hook(repo_path: str | Path, commit: dict[str, Any]) -> None:
    """为当前计划 commit 运行 pre-commit，并把失败关联到具体 commit。"""
    try:
        run_git(repo_path, ["hook", "run", "--ignore-missing", "pre-commit"])
    except BatchPlanError as exc:
        raise BatchPlanError(
            f"pre-commit hook failed for {describe_commit(commit)}: {exc}"
        ) from exc



def ensure_hook_result_is_absorbable(
    repo_path: str | Path,
    validation: dict[str, Any],
    commit: dict[str, Any],
    *,
    before_hunk_entries: str,
) -> None:
    """校验 hook 后的 staged snapshot 是否仍处于当前 commit 边界内。

    Example:
        ensure_hook_result_is_absorbable(
            worktree_path,
            validation,
            commit,
            before_hunk_entries=before_hunk_entries,
        )
    """
    label = describe_commit(commit)
    allowed_paths = commit_allowed_paths(validation, commit)

    staged = staged_paths(repo_path)
    staged_outside = sorted(staged - allowed_paths)
    if staged_outside:
        raise BatchPlanError(
            f"pre-commit hook modified paths outside {label}: "
            f"{', '.join(staged_outside)}"
        )

    unstaged = unstaged_paths(repo_path)
    if unstaged:
        raise BatchPlanError(
            f"pre-commit hook left unstaged changes for {label}: "
            f"{', '.join(sorted(unstaged))}"
        )

    untracked = untracked_paths(repo_path)
    if untracked:
        outside = sorted(untracked - allowed_paths)
        if outside:
            raise BatchPlanError(
                f"pre-commit hook created untracked paths outside {label}: "
                f"{', '.join(outside)}"
            )
        raise BatchPlanError(
            f"pre-commit hook left untracked changes for {label}: "
            f"{', '.join(sorted(untracked))}"
        )

    hunk_paths = commit_hunk_paths(validation, commit)
    if hunk_paths and before_hunk_entries != index_entries(repo_path, hunk_paths):
        raise BatchPlanError(
            f"pre-commit hook modified hunk-split file for {label}: "
            f"{', '.join(sorted(hunk_paths))}"
        )



def create_commits_with_temp_index(
    repo_path: str | Path, validation: dict[str, Any]
) -> tuple[str, str, list[dict[str, str]]]:
    """在 shadow worktree 中运行 hook 并构造整组 commit，但先不移动主仓库 HEAD。

    Example:
        start_head, final_commit, commits = create_commits_with_temp_index(
            repo_path,
            validation,
        )
    """
    start_head = validation["inventory"]["base_head"]
    final_commit = start_head
    created_commits: list[dict[str, str]] = []

    with shadow_worktree(repo_path, start_head) as worktree_path:
        for commit in validation["commits"]:
            apply_commit_to_worktree(worktree_path, validation, commit)
            before_hunk_entries = index_entries(
                worktree_path,
                commit_hunk_paths(validation, commit),
            )
            run_pre_commit_hook(worktree_path, commit)
            ensure_hook_result_is_absorbable(
                worktree_path,
                validation,
                commit,
                before_hunk_entries=before_hunk_entries,
            )

            tree = run_git(worktree_path, ["write-tree"]).strip()
            final_commit = run_git(
                worktree_path,
                ["commit-tree", tree, "-p", final_commit],
                input_text=commit["message"]["full_text"],
            ).strip()
            stored_message = run_git(
                worktree_path,
                ["log", "-1", "--pretty=%B", final_commit],
            )
            validate_commit_message_text(stored_message)
            run_git(worktree_path, ["reset", "--hard", "--quiet", final_commit])
            created_commits.append(
                {
                    "id": commit["id"],
                    "commit": final_commit,
                    "header": commit["message"]["header"],
                }
            )

    return start_head, final_commit, created_commits



def restore_index(index_path: str | Path, backup_path: Path | None) -> None:
    """把真实 index 恢复到 apply 前的状态。"""
    if backup_path and backup_path.exists():
        shutil.copyfile(backup_path, index_path)
        return

    if Path(index_path).exists():
        Path(index_path).unlink()



def sync_worktree_paths(repo_path: str | Path, paths: set[str]) -> None:
    """把指定路径的工作区内容同步到当前 index。"""
    repo_root = Path(repo_path)
    for path in sorted(paths):
        if not path or Path(path).is_absolute() or ".." in Path(path).parts:
            raise BatchPlanError(f"unsafe worktree sync path: {path}")

        if path_is_tracked(repo_path, path):
            run_git(repo_path, ["checkout-index", "--force", "--", path])
            continue

        target = repo_root / path
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()



def apply_commits_transaction(
    repo_path: str | Path,
    start_head: str,
    final_commit: str,
    *,
    worktree_paths: set[str] | None = None,
) -> None:
    """以事务方式把临时构造好的 commit 链正式落到当前仓库。

    Example:
        apply_commits_transaction(repo_path, start_head, final_commit)
    """
    raw_index_path = Path(
        run_git(repo_path, ["rev-parse", "--git-path", "index"]).strip()
    )
    index_path = raw_index_path if raw_index_path.is_absolute() else Path(repo_path) / raw_index_path
    backup_path: Path | None = None

    if index_path.exists():
        with tempfile.NamedTemporaryFile(
            prefix="emoji-commit-index-backup-",
            delete=False,
        ) as handle:
            backup_path = Path(handle.name)
        shutil.copyfile(index_path, backup_path)

    updated_ref = False
    try:
        # 只有整组 commit 都构造完成后才真正移动 HEAD。
        # 如果后续 read-tree 刷新工作区快照失败，就把 HEAD 和磁盘 index 一起回滚。
        run_git(
            repo_path,
            ["update-ref", "-m", "emoji-commit batch apply", "HEAD", final_commit, start_head],
        )
        updated_ref = True
        run_git(repo_path, ["read-tree", final_commit])
        if worktree_paths:
            sync_worktree_paths(repo_path, worktree_paths)
    except Exception:
        if updated_ref:
            try:
                run_git(
                    repo_path,
                    [
                        "update-ref",
                        "-m",
                        "emoji-commit batch rollback",
                        "HEAD",
                        start_head,
                        final_commit,
                    ],
                )
            except Exception:
                pass
        restore_index(index_path, backup_path)
        raise
    finally:
        if backup_path and backup_path.exists():
            backup_path.unlink()
