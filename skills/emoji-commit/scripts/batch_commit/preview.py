from __future__ import annotations

from typing import Any

from batch_commit.constants import (
    DEFAULT_EMOJI_COMMIT_LANGUAGE,
    REPO_SKILL_PACKAGES_GROUP,
    SUPPORTED_EMOJI_COMMIT_LANGUAGES,
)


def preview_language(validation: dict[str, Any]) -> str:
    """解析 preview 可用的提交描述语言，缺省时沿用英文。"""
    config = validation.get("config")
    if not isinstance(config, dict):
        config = validation["inventory"].get("config", {})
    language = str(config.get("emoji_commit_language", DEFAULT_EMOJI_COMMIT_LANGUAGE))
    if language not in SUPPORTED_EMOJI_COMMIT_LANGUAGES:
        return DEFAULT_EMOJI_COMMIT_LANGUAGE
    return language



def skill_snapshot_suggested_header(language: str) -> str:
    """返回 repo skill package snapshot 的默认提交标题。"""
    if language == "zh":
        return ":sparkles: (skills) 更新项目技能"
    return ":sparkles: (skills) update repo skill packages"



def build_skill_snapshot_preview(validation: dict[str, Any]) -> list[str]:
    """构建 `.agents/skills/*` 领域语义的 preview 摘要。

    Example:
        lines = build_skill_snapshot_preview(validation)
    """
    files = validation["inventory"]["files"]
    snapshot_files = [
        file_record
        for file_record in files
        if file_record.get("recommended_group") == REPO_SKILL_PACKAGES_GROUP
    ]
    if not snapshot_files:
        return []

    language = preview_language(validation)
    suggested_header = skill_snapshot_suggested_header(language)
    non_snapshot_count = len(files) - len(snapshot_files)

    skill_records: dict[str, dict[str, Any]] = {}
    for file_record in snapshot_files:
        skill_name = str(file_record.get("skill_name") or "(unknown)")
        record = skill_records.setdefault(
            skill_name,
            {
                "origin": file_record.get("skill_origin", "unknown"),
                "warnings": set(),
            },
        )
        record["warnings"].update(file_record.get("warnings", []))

    lines = [
        "Repo skill package snapshot detected:",
        "These .agents/skills/* changes look like repo skill package updates, not application code.",
        f"Suggested grouping: {suggested_header}",
    ]
    if non_snapshot_count > 0:
        lines.append(
            "Suggested split: keep repo skill package updates separate from business/application changes."
        )

    lines.append("Skills:")
    for skill_name in sorted(skill_records):
        record = skill_records[skill_name]
        lines.append(f"- {skill_name}: {record['origin']}")

    suspicious: list[str] = []
    for file_record in snapshot_files:
        for warning in file_record.get("warnings", []):
            suspicious.append(f"- {file_record['path']}: {warning}")
    if suspicious:
        lines.append("Suspicious/noise:")
        lines.extend(sorted(dict.fromkeys(suspicious)))

    lines.append("")
    return lines



def build_preview_text(validation: dict[str, Any]) -> str:
    """把校验后的计划渲染成给用户确认的纯文本预览。

    Example:
        preview_text = build_preview_text(validation)
    """
    inventory = validation["inventory"]
    units_by_id = validation["units_by_id"]
    files_by_path = validation["files_by_path"]

    lines = [
        "emoji-commit batch preview",
        f"Base HEAD: {inventory['base_head']}",
        f"Input scope: {validation['input_scope']}",
        "Status: waiting for confirmation, no commits have been created.",
        "",
    ]
    lines.extend(build_skill_snapshot_preview(validation))

    for index, commit in enumerate(validation["commits"], start=1):
        lines.append(f"{index}. {commit['message']['header']}")
        lines.append(f"Reason: {commit['reason']}")
        lines.append(f"Split mode: {commit['split_mode']}")
        has_partial_split = any(
            units_by_id[unit_id]["partial_split_supported"]
            for unit_id in commit["units"]
        )
        lines.append(f"Partial split: {'yes' if has_partial_split else 'no'}")
        lines.append("Coverage:")
        for unit_id in commit["units"]:
            unit = units_by_id[unit_id]
            file_record = files_by_path[unit["path"]]
            if unit["kind"] == "hunk":
                lines.append(f"- {unit['path']} {unit['summary']}")
                continue

            if file_record["change_type"] == "R":
                label = f"{file_record['old_path']} -> {file_record['new_path']}"
            else:
                label = unit["path"]
            lines.append(f"- {label} ({file_record['change_type']})")

        lines.append("Body:")
        if commit["message"]["body"]:
            lines.extend(f"- {item}" for item in commit["message"]["body"])
        else:
            lines.append("- (no body items)")
        lines.append("")

    return "\n".join(lines) + "\n"
