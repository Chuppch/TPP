from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from batch_commit.config import load_skills_lock
from batch_commit.constants import AGENT_SKILLS_PREFIX, REPO_SKILL_PACKAGES_GROUP
from batch_commit.diff_parser import (
    build_untracked_patch_blocks,
    diff_is_whitespace_only,
    parse_file_patch,
    split_patch_blocks,
)
from batch_commit.errors import BatchPlanError
from batch_commit.git_utils import resolve_repo_root, run_git


def parse_agent_skill_path(path: str) -> tuple[str, Path] | None:
    """从 `.agents/skills/<name>/...` 路径中解析 skill 名称和根目录。

    Example:
        parse_agent_skill_path(".agents/skills/foo/SKILL.md")
        # => ("foo", Path(".agents/skills/foo"))
    """
    if path == ".agents/skills" or not path.startswith(AGENT_SKILLS_PREFIX):
        return None

    suffix = path[len(AGENT_SKILLS_PREFIX) :]
    skill_name = suffix.split("/", 1)[0].strip()
    if not skill_name:
        return None

    return skill_name, Path(".agents") / "skills" / skill_name



def skill_lock_has_source(lock_entry: Any) -> bool:
    """判断 skills-lock entry 是否含有足够强的来源信号。"""
    if not isinstance(lock_entry, dict):
        return False
    return any(
        str(lock_entry.get(key, "")).strip()
        for key in ("sourceUrl", "sourceType", "computedHash", "skillPath")
    )



def symlink_points_to_source(
    repo_root: str | Path,
    skill_root: Path,
    skill_name: str,
) -> bool:
    """判断 `.agents/skills/<name>` 是否是指向 `skills/<name>` 的 symlink。"""
    absolute_root = Path(repo_root) / skill_root
    if not absolute_root.is_symlink():
        return False

    try:
        link_target = os.readlink(absolute_root)
    except OSError:
        return False

    target_path = Path(link_target)
    if not target_path.is_absolute():
        target_path = (absolute_root.parent / target_path).resolve()

    return target_path == (Path(repo_root) / "skills" / skill_name).resolve()



def parse_skill_frontmatter_name(skill_md_path: Path) -> tuple[str | None, str | None]:
    """解析 SKILL.md frontmatter 的 name 字段；失败时返回 warning。"""
    if not skill_md_path.exists() or not skill_md_path.is_file():
        return None, None

    try:
        lines = skill_md_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return None, f"unable to read SKILL.md frontmatter: {exc}"

    if not lines or lines[0].strip() != "---":
        return None, None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None, None
        if stripped.startswith("name:"):
            value = stripped[len("name:") :].strip().strip("\"'")
            return value or None, None

    return None, None



def annotate_agent_skill_file(
    repo_root: str | Path,
    file_record: dict[str, Any],
    file_units: list[dict[str, Any]],
    skills_lock: dict[str, Any],
    lock_warnings: list[str],
) -> None:
    """为 `.agents/skills/*` 文件记录补充 skill snapshot 领域标注。

    Example:
        annotate_agent_skill_file(repo_root, file_record, file_units, skills_lock, [])
    """
    parsed = parse_agent_skill_path(str(file_record["path"]))
    if not parsed:
        return

    skill_name, skill_root = parsed
    absolute_root = Path(repo_root) / skill_root
    source_dir = Path(repo_root) / "skills" / skill_name
    skill_md_path = absolute_root / "SKILL.md"
    warnings = list(lock_warnings)
    lock_entry = skills_lock.get(skill_name)
    has_lock_source = skill_lock_has_source(lock_entry)
    points_to_source = symlink_points_to_source(repo_root, skill_root, skill_name)

    if points_to_source:
        skill_origin = "source-symlink"
    elif has_lock_source:
        skill_origin = "external-lock-managed"
    elif skill_md_path.exists() and not source_dir.exists():
        skill_origin = "repo-installed-skill"
    else:
        skill_origin = "ambiguous-skill-dir"
        warnings.append("ambiguous-skill-dir")

    if skill_origin in {"external-lock-managed", "repo-installed-skill"}:
        file_record["recommended_group"] = REPO_SKILL_PACKAGES_GROUP

    frontmatter_name, frontmatter_warning = parse_skill_frontmatter_name(skill_md_path)
    if frontmatter_warning:
        warnings.append(frontmatter_warning)
    if frontmatter_name and frontmatter_name != skill_name:
        warnings.append(
            f"suspicious-frontmatter: SKILL.md name is {frontmatter_name}, expected {skill_name}"
        )

    if has_lock_source and not skill_md_path.exists() and not points_to_source:
        warnings.append("suspicious-lock-drift: lock entry exists but SKILL.md is missing")

    if source_dir.exists() and not points_to_source and not has_lock_source:
        warnings.append("suspicious-installed-copy: matching skills source exists without symlink")

    if diff_is_whitespace_only([unit["patch"] for unit in file_units]):
        warnings.append("whitespace-only")

    file_record.update(
        {
            "domain": "agent-skill",
            "skill_name": skill_name,
            "skill_root": str(skill_root),
            "skill_origin": skill_origin,
        }
    )
    if warnings:
        file_record["warnings"] = sorted(dict.fromkeys(warnings))



def build_inventory(
    repo_path: str | Path,
    base_ref: str,
    input_scope: str = "worktree",
) -> dict[str, Any]:
    """基于 base_ref 收集 staged 或整个 worktree 的变更清单。

    Example:
        inventory = build_inventory(repo_path, "HEAD", "worktree")
        unit_count = inventory["stats"]["unit_count"]
    """
    if input_scope not in {"staged", "worktree"}:
        raise BatchPlanError(f"unsupported input_scope: {input_scope}")

    repo_root = resolve_repo_root(repo_path)
    base_head = run_git(repo_path, ["rev-parse", base_ref]).strip()
    skills_lock, skills_lock_warnings = load_skills_lock(repo_root)

    if input_scope == "staged":
        diff_text = run_git(
            repo_path,
            [
                "diff",
                "--cached",
                "--binary",
                "--full-index",
                "--no-color",
                "--find-renames",
                "--no-ext-diff",
                base_ref,
                "--",
            ],
        )
    else:
        diff_text = run_git(
            repo_path,
            [
                "diff",
                "--binary",
                "--full-index",
                "--no-color",
                "--find-renames",
                "--no-ext-diff",
                base_ref,
                "--",
            ],
        )

    patch_blocks = split_patch_blocks(diff_text)

    if input_scope == "worktree":
        untracked = run_git(
            repo_path,
            ["ls-files", "--others", "--exclude-standard", "-z"],
        )
        patch_blocks.extend(
            build_untracked_patch_blocks(
                repo_path,
                base_head,
                untracked.split("\0"),
            )
        )

    files: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    for block in patch_blocks:
        file_record, file_units = parse_file_patch(block)
        annotate_agent_skill_file(
            repo_root,
            file_record,
            file_units,
            skills_lock,
            skills_lock_warnings,
        )
        files.append(file_record)
        units.extend(file_units)

    return {
        "base_ref": base_ref,
        "base_head": base_head,
        "input_scope": input_scope,
        "files": files,
        "units": units,
        "stats": {
            "file_count": len(files),
            "unit_count": len(units),
        },
    }
