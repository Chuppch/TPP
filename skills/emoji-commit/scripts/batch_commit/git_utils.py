from __future__ import annotations

import os
import subprocess
from pathlib import Path

from batch_commit.errors import BatchPlanError


def run_git(
    repo_path: str | Path,
    args: list[str],
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    allow_returncodes: tuple[int, ...] = (0,),
) -> str:
    """在指定仓库中执行 git 命令，并把失败统一转成 BatchPlanError。

    Example:
        run_git(repo_path, ["rev-parse", "HEAD"]).strip()
    """
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        env=merged_env,
        input=input_text,
        text=True,
        capture_output=True,
    )

    if result.returncode not in allow_returncodes:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"git {' '.join(args)} failed"
        )
        raise BatchPlanError(message)

    return result.stdout



def split_nul_paths(output: str) -> list[str]:
    """解析 Git `-z` 输出的路径列表。"""
    return [path for path in output.split("\0") if path]



def list_git_paths(
    repo_path: str | Path,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> set[str]:
    """执行返回 NUL 分隔路径的 Git 命令，并收敛成集合。

    Example:
        list_git_paths(repo_path, ["diff", "--name-only", "-z"])
    """
    return set(split_nul_paths(run_git(repo_path, args, env=env)))



def resolve_repo_root(repo_path: str | Path) -> Path:
    """解析目标 Git 仓库根目录，配置读取必须以它为基准。

    Example:
        repo_root = resolve_repo_root(".")
    """
    root = run_git(repo_path, ["rev-parse", "--show-toplevel"]).strip()
    if not root:
        raise BatchPlanError("unable to resolve repository root")
    return Path(root)



def path_is_ignored(repo_root: str | Path, relative_path: str | Path) -> bool:
    """检查指定相对路径是否被 Git 忽略规则覆盖。"""
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "--quiet",
            "--",
            str(relative_path),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if result.returncode in {0, 1}:
        return result.returncode == 0
    message = result.stderr.strip() or "git check-ignore failed"
    raise BatchPlanError(message)



def path_is_tracked(repo_root: str | Path, relative_path: str | Path) -> bool:
    """检查路径是否已经进入 Git index。"""
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            "--",
            str(relative_path),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if result.returncode in {0, 1}:
        return result.returncode == 0
    message = result.stderr.strip() or "git ls-files failed"
    raise BatchPlanError(message)



def staged_paths(repo_path: str | Path) -> set[str]:
    """返回当前 index 相对 HEAD 的 staged 路径集合。"""
    return list_git_paths(repo_path, ["diff", "--cached", "--name-only", "-z"])



def unstaged_paths(repo_path: str | Path) -> set[str]:
    """返回工作区相对 index 的 unstaged 路径集合。"""
    return list_git_paths(repo_path, ["diff", "--name-only", "-z"])



def untracked_paths(repo_path: str | Path) -> set[str]:
    """返回未被忽略的 untracked 路径集合。"""
    return list_git_paths(repo_path, ["ls-files", "--others", "--exclude-standard", "-z"])



def index_entries(repo_path: str | Path, paths: set[str]) -> str:
    """读取指定路径在 index 中的原始条目，用于判断 hook 是否改写 hunk 文件。"""
    if not paths:
        return ""
    return run_git(repo_path, ["ls-files", "-s", "-z", "--", *sorted(paths)])
