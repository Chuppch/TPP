from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from batch_commit.constants import (
    DEFAULT_EMOJI_COMMIT_LANGUAGE,
    FEX_SKILLS_CONFIG_PATH,
    FEX_SKILLS_LOCAL_CONFIG_PATH,
    SKILLS_LOCK_PATH,
    SUPPORTED_EMOJI_COMMIT_LANGUAGES,
)
from batch_commit.errors import BatchPlanError
from batch_commit.git_utils import path_is_ignored, path_is_tracked, resolve_repo_root


def enforce_local_config_gate(repo_path: str | Path) -> Path:
    """本地配置存在时，要求它被忽略且未进入 index。

    Example:
        repo_root = enforce_local_config_gate(repo_path)
    """
    repo_root = resolve_repo_root(repo_path)
    local_config = repo_root / FEX_SKILLS_LOCAL_CONFIG_PATH
    if not local_config.exists():
        return repo_root

    if not path_is_ignored(repo_root, FEX_SKILLS_LOCAL_CONFIG_PATH):
        raise BatchPlanError(
            ".agents/fex-skills.config.local.json is local-only; add it to .gitignore "
            "or remove the local config before running emoji-commit"
        )

    if path_is_tracked(repo_root, FEX_SKILLS_LOCAL_CONFIG_PATH):
        raise BatchPlanError(
            ".agents/fex-skills.config.local.json is local-only but is tracked by Git; "
            "remove it from the index before running emoji-commit"
        )

    return repo_root



def deep_merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并配置对象，非对象或类型冲突时 override 优先。"""
    merged = dict(base)
    for key, override_value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = deep_merge_config(base_value, override_value)
        else:
            merged[key] = override_value
    return merged



def load_optional_config_file(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    """读取可选配置文件；异常不阻断，交给语言默认值兜底。"""
    config_path = Path(path)
    if not config_path.exists():
        return {}, []

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        return {}, [f"invalid FEX skills config JSON: {config_path}: {exc}"]

    if not isinstance(data, dict):
        return {}, [f"FEX skills config must be a JSON object: {config_path}"]

    return data, []



def load_skills_lock(repo_root: str | Path) -> tuple[dict[str, Any], list[str]]:
    """读取 skills-lock.json；异常降级为 warning，避免阻断 inventory。"""
    lock_path = Path(repo_root) / SKILLS_LOCK_PATH
    if not lock_path.exists():
        return {}, []

    try:
        with lock_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        return {}, [f"invalid skills-lock.json: {exc}"]

    if not isinstance(data, dict):
        return {}, ["skills-lock.json must be a JSON object"]

    skills = data.get("skills", {})
    if not isinstance(skills, dict):
        return {}, ["skills-lock.json skills must be an object"]

    return skills, []



def load_fex_skills_config(repo_path: str | Path) -> tuple[dict[str, Any], list[str], Path]:
    """读取项目配置和本地配置，并返回递归合并后的结果。

    Example:
        config, warnings, repo_root = load_fex_skills_config(repo_path)
    """
    repo_root = resolve_repo_root(repo_path)
    project_config, project_warnings = load_optional_config_file(
        repo_root / FEX_SKILLS_CONFIG_PATH
    )
    local_config, local_warnings = load_optional_config_file(
        repo_root / FEX_SKILLS_LOCAL_CONFIG_PATH
    )
    return (
        deep_merge_config(project_config, local_config),
        [*project_warnings, *local_warnings],
        repo_root,
    )



def resolve_emoji_commit_language(
    config: dict[str, Any],
) -> tuple[str, list[str]]:
    """从合并后的 FEX skills 配置中解析 emoji-commit 语言偏好。

    Example:
        language, warnings = resolve_emoji_commit_language(config)
    """
    emoji_commit_config = config.get("emoji-commit")
    if emoji_commit_config is None:
        return DEFAULT_EMOJI_COMMIT_LANGUAGE, []
    if not isinstance(emoji_commit_config, dict):
        return (
            DEFAULT_EMOJI_COMMIT_LANGUAGE,
            ["emoji-commit config must be an object; fallback to en"],
        )

    language = emoji_commit_config.get("language", DEFAULT_EMOJI_COMMIT_LANGUAGE)
    if language is None:
        return DEFAULT_EMOJI_COMMIT_LANGUAGE, []

    language_text = str(language).strip()
    if language_text in SUPPORTED_EMOJI_COMMIT_LANGUAGES:
        return language_text, []

    return (
        DEFAULT_EMOJI_COMMIT_LANGUAGE,
        [
            f'emoji-commit language config "{language_text}" is unsupported; '
            "fallback to en"
        ],
    )



def resolve_config_context(
    repo_path: str | Path,
    *,
    enforce_gate: bool = True,
) -> dict[str, Any]:
    """解析配置上下文，供 inventory、preview 和 apply 统一使用。

    Example:
        context = resolve_config_context(repo_path)
        language = context["language"]
    """
    repo_root = enforce_local_config_gate(repo_path) if enforce_gate else resolve_repo_root(repo_path)
    config, config_warnings, _ = load_fex_skills_config(repo_root)
    language, language_warnings = resolve_emoji_commit_language(config)
    return {
        "repo_root": repo_root,
        "config": config,
        "language": language,
        "warnings": [*config_warnings, *language_warnings],
    }
