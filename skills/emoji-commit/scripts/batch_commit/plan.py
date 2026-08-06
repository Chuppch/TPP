from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from batch_commit.errors import BatchPlanError
from batch_commit.git_utils import run_git
from batch_commit.inventory import build_inventory
from batch_commit.message import (
    build_commit_message,
    extract_jira_keys,
    normalize_body_item,
)


def load_json_file(path: str | Path) -> dict[str, Any]:
    """读取计划文件，并把常见文件/JSON 错误转成业务错误。

    Example:
        plan = load_json_file("batch-plan.json")
    """
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise BatchPlanError(f"plan file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BatchPlanError(f"invalid plan JSON: {exc}") from exc



def validate_plan(repo_path: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    """校验批次计划，并补齐 apply/preview 所需的规范化数据。

    Example:
        validation = validate_plan(repo_path, plan)
        commits = validation["commits"]
    """
    commits = plan.get("commits")
    if not isinstance(commits, list) or not commits:
        raise BatchPlanError("plan must contain a non-empty commits array")

    current_head = run_git(repo_path, ["rev-parse", "HEAD"]).strip()
    plan_head = str(plan.get("base_head", "")).strip()
    if not plan_head:
        raise BatchPlanError("plan.base_head is required")
    if current_head != plan_head:
        raise BatchPlanError(
            f"HEAD changed since preview: expected {plan_head}, got {current_head}"
        )

    input_scope = str(plan.get("input_scope", "")).strip()
    if input_scope not in {"staged", "worktree"}:
        raise BatchPlanError("plan.input_scope must be either 'staged' or 'worktree'")

    inventory = build_inventory(repo_path, "HEAD", input_scope)
    units_by_id = {unit["id"]: unit for unit in inventory["units"]}
    files_by_path = {file_record["path"]: file_record for file_record in inventory["files"]}

    assigned: dict[str, str] = {}
    commit_ids: set[str] = set()
    normalized_commits: list[dict[str, Any]] = []

    for commit in commits:
        commit_id = str(commit.get("id", "")).strip()
        if not commit_id:
            raise BatchPlanError("each commit requires a stable id")
        if commit_id in commit_ids:
            raise BatchPlanError(f"duplicate commit id: {commit_id}")
        commit_ids.add(commit_id)

        split_mode = commit.get("split_mode")
        if split_mode not in {"file", "hunk"}:
            raise BatchPlanError(
                f"unsupported split_mode for {commit_id}: {split_mode}"
            )

        reason = str(commit.get("reason", "")).strip()
        if not reason:
            raise BatchPlanError(f"commit {commit_id} must include a reason")

        units = commit.get("units")
        if not isinstance(units, list) or not units:
            raise BatchPlanError(
                f"commit {commit_id} must include at least one unit"
            )

        normalized_units: list[str] = []
        for unit_id in units:
            normalized_unit_id = str(unit_id).strip()
            if normalized_unit_id not in units_by_id:
                raise BatchPlanError(
                    f"commit {commit_id} references unknown unit: {normalized_unit_id}"
                )
            if normalized_unit_id in assigned:
                raise BatchPlanError(
                    f"unit {normalized_unit_id} is assigned more than once"
                )
            assigned[normalized_unit_id] = commit_id
            normalized_units.append(normalized_unit_id)

        message_data = commit.get("message")
        if not isinstance(message_data, dict):
            raise BatchPlanError(
                f"commit {commit_id} must include message.header and message.body"
            )

        full_message = build_commit_message(message_data)
        normalized_body = []
        body_value = message_data.get("body", [])
        if body_value is None:
            body_value = []
        if isinstance(body_value, str):
            body_value = [body_value]
        for item in body_value:
            if str(item).strip():
                normalized_body.append(normalize_body_item(item))

        normalized_commits.append(
            {
                "id": commit_id,
                "reason": reason,
                "split_mode": split_mode,
                "units": normalized_units,
                "message": {
                    "header": str(message_data.get("header", "")).strip(),
                    "body": normalized_body,
                    "jira_refs": extract_jira_keys(message_data.get("jira_refs", [])),
                    "full_text": full_message,
                },
            }
        )

    inventory_unit_ids = set(units_by_id)
    assigned_ids = set(assigned)
    missing_units = sorted(inventory_unit_ids - assigned_ids)
    extra_units = sorted(assigned_ids - inventory_unit_ids)
    if missing_units or extra_units:
        details = []
        if missing_units:
            details.append(f"missing units: {', '.join(missing_units)}")
        if extra_units:
            details.append(f"unexpected units: {', '.join(extra_units)}")
        raise BatchPlanError("; ".join(details))

    for commit in normalized_commits:
        if commit["split_mode"] == "file":
            units_by_path: dict[str, set[str]] = defaultdict(set)
            for unit_id in commit["units"]:
                units_by_path[units_by_id[unit_id]["path"]].add(unit_id)
            for path, commit_unit_ids in units_by_path.items():
                file_record = files_by_path[path]
                file_unit_ids = set(file_record["unit_ids"])
                # file 模式是严格全量覆盖：既然声称“这个 commit 接管整个文件”，
                # 那就不能留下同文件的其他 unit 给后续 commit 捡漏。
                if commit_unit_ids != file_unit_ids:
                    raise BatchPlanError(
                        f"commit {commit['id']} uses split_mode=file but does not cover full file: {path}"
                    )
        else:
            for unit_id in commit["units"]:
                unit = units_by_id[unit_id]
                file_record = files_by_path[unit["path"]]
                # hunk 模式只允许作用在 inventory 阶段已经标记为“可安全局部拆分”
                # 的文本修改上，避免把危险 patch 强拆开。
                if unit["kind"] != "hunk" or not file_record["partial_split_supported"]:
                    raise BatchPlanError(
                        f"commit {commit['id']} uses split_mode=hunk with unsupported unit: {unit_id}"
                    )

    return {
        "input_scope": input_scope,
        "inventory": inventory,
        "units_by_id": units_by_id,
        "files_by_path": files_by_path,
        "commits": normalized_commits,
    }
