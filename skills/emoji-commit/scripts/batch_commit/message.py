from __future__ import annotations

import os
import re
from typing import Any

from batch_commit.constants import (
    BREAKING_CHANGE_PATTERN,
    FORBIDDEN_COAUTHOR_PATTERN,
    HEADER_PATTERN,
    JIRA_KEY_PATTERN,
    JIRA_REFS_PATTERN,
    JIRA_URL_PATTERN,
    TRAILER_PATTERN,
)
from batch_commit.errors import BatchPlanError


def resolve_agent_name() -> str:
    """按既定优先级推断 AI-Co-Authored-By 的代理名称。"""
    for key in ("COMMIT_AI_AGENT_NAME", "AI_AGENT_NAME", "AGENT_NAME"):
        value = os.getenv(key)
        if value:
            return value

    prefix_map = (
        ("OPENAI_", "Codex"),
        ("CODEX_", "Codex"),
        ("ANTHROPIC_", "Claude"),
        ("CLAUDE_", "Claude"),
        ("MINMAX_", "MinMax"),
        ("GOOGLE_", "Gemini"),
        ("GEMINI_", "Gemini"),
    )
    for key in os.environ:
        for prefix, display_name in prefix_map:
            if key.startswith(prefix):
                return display_name

    return "AI Agent"



def sanitize_agent_name(agent_name: str) -> str:
    """清洗代理名称，避免 trailer 被换行或冒号污染。"""
    value = str(agent_name or "").strip()
    value = re.sub(r"[\r\n\x00-\x1f\x7f]+", " ", value)
    value = value.replace(":", "-")
    value = re.sub(r"\s+", " ", value).strip()
    return value or "AI Agent"



def normalize_body_item(item: Any) -> str:
    """把 body 条目标准化成无前缀、单行的 bullet 内容。"""
    text = str(item).strip()
    text = re.sub(r"^[-*]\s*", "", text)
    return text



def extract_jira_keys(value: Any) -> list[str]:
    """从 Jira URL / Jira Key 混合输入中提取、去重并保持首次出现顺序。

    Example:
        extract_jira_keys(["FEX-1", "https://jira.meitu.com/browse/FEX-2"])
        # => ["FEX-1", "FEX-2"]
    """
    if value is None:
        raw_items: list[Any] = []
    elif isinstance(value, str):
        raw_items = [value]
    else:
        try:
            raw_items = list(value)
        except TypeError:
            raw_items = [value]

    ordered_keys: list[str] = []
    seen: set[str] = set()

    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue

        matches: list[tuple[int, str]] = []
        for match in JIRA_URL_PATTERN.finditer(text):
            matches.append((match.start(1), match.group(1)))
        for match in JIRA_KEY_PATTERN.finditer(text):
            matches.append((match.start(1), match.group(1)))

        for _, key in sorted(matches, key=lambda pair: pair[0]):
            if key not in seen:
                seen.add(key)
                ordered_keys.append(key)

    return ordered_keys



def normalize_jira_refs(value: Any) -> str:
    """把 Jira 输入归一成单行 Jira-Refs trailer；没有 key 时返回空字符串。

    Example:
        normalize_jira_refs(["FEX-1", "FEX-2"])
        # => "Jira-Refs: FEX-1, FEX-2"
    """
    jira_keys = extract_jira_keys(value)
    if not jira_keys:
        return ""
    return f"Jira-Refs: {', '.join(jira_keys)}"



def build_commit_message(message_data: dict[str, Any]) -> str:
    """把 header/body 组装成最终 commit message，并追加 AI trailer。

    Example:
        build_commit_message({
            "header": ":sparkles: add batch preview",
            "body": ["render preview before apply"],
        })
    """
    if not isinstance(message_data, dict):
        raise BatchPlanError("message must be an object")

    header = str(message_data.get("header", "")).strip()
    if not header:
        raise BatchPlanError("message.header is required")

    body_value = message_data.get("body", [])
    if body_value is None:
        raw_body_items: list[Any] = []
    elif isinstance(body_value, str):
        raw_body_items = [body_value]
    else:
        try:
            raw_body_items = list(body_value)
        except TypeError:
            raw_body_items = [body_value]

    body_items = [
        normalize_body_item(item)
        for item in raw_body_items
        if str(item).strip()
    ]
    # 这是当前执行器的紧凑输出限制，不是 header/footer 语法本身的一部分。
    # 继续保留它，避免 batch preview 与最终消息在 CLI 中膨胀成过长正文。
    if len(body_items) > 5:
        raise BatchPlanError("commit body may include at most 5 items")

    breaking_change = str(message_data.get("breaking_change", "")).strip()
    if breaking_change:
        breaking_change = re.sub(r"[\r\n]+", " ", breaking_change)
        breaking_change = re.sub(r"\s+", " ", breaking_change).strip()
        if not breaking_change:
            raise BatchPlanError("message.breaking_change must not be empty")

    jira_refs = normalize_jira_refs(message_data.get("jira_refs", []))

    trailer = f"AI-Co-Authored-By: {sanitize_agent_name(resolve_agent_name())}"
    lines = [header, ""]
    if body_items:
        lines.extend(f"- {item}" for item in body_items)
        lines.append("")
    if jira_refs:
        lines.append(jira_refs)
        lines.append("")
    if breaking_change:
        lines.append(f"BREAKING CHANGE: {breaking_change}")
        lines.append("")
    lines.append(trailer)
    full_text = "\n".join(lines) + "\n"
    validate_commit_message_text(full_text)
    return full_text



def validate_commit_message_text(message: str) -> None:
    """校验 commit message 是否满足 emoji-commit 的格式约束。

    Example:
        validate_commit_message_text(full_commit_message)
    """
    lines = message.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()

    if not lines:
        raise BatchPlanError("commit message is empty")

    header = lines[0]
    if not HEADER_PATTERN.match(header):
        raise BatchPlanError(f"invalid commit header: {header}")

    if len(lines) < 2 or lines[1] != "":
        raise BatchPlanError("commit message must contain a blank line after the header")

    trailer_indexes = [
        index for index, line in enumerate(lines) if TRAILER_PATTERN.match(line)
    ]
    if len(trailer_indexes) != 1:
        raise BatchPlanError(
            "commit message must contain exactly one AI-Co-Authored-By trailer"
        )

    breaking_indexes = [
        index for index, line in enumerate(lines) if BREAKING_CHANGE_PATTERN.match(line)
    ]
    if len(breaking_indexes) > 1:
        raise BatchPlanError(
            "commit message may contain at most one BREAKING CHANGE footer"
        )

    jira_refs_indexes = [
        index for index, line in enumerate(lines) if JIRA_REFS_PATTERN.match(line)
    ]
    if len(jira_refs_indexes) > 1:
        raise BatchPlanError(
            "commit message may contain at most one Jira-Refs footer"
        )

    if any(FORBIDDEN_COAUTHOR_PATTERN.match(line) for line in lines):
        raise BatchPlanError(
            "commit message must not contain Co-authored-by trailers"
        )

    trailer_index = trailer_indexes[0]
    jira_refs_index = jira_refs_indexes[0] if jira_refs_indexes else None
    breaking_index = breaking_indexes[0] if breaking_indexes else None

    if jira_refs_index is not None:
        if jira_refs_index == 0 or lines[jira_refs_index - 1] != "":
            raise BatchPlanError(
                "commit message must contain a blank line before the footer block"
            )
        if breaking_index is not None:
            if jira_refs_index >= breaking_index:
                raise BatchPlanError(
                    "Jira-Refs footer must appear before BREAKING CHANGE"
                )
            if jira_refs_index + 1 != breaking_index - 1 or lines[jira_refs_index + 1] != "":
                raise BatchPlanError(
                    "Jira-Refs footer must be separated from BREAKING CHANGE by a blank line"
                )
        elif jira_refs_index != trailer_index - 2 or lines[jira_refs_index + 1] != "":
            raise BatchPlanError(
                "Jira-Refs footer must be separated from the AI-Co-Authored-By trailer by a blank line"
            )

    if breaking_index is not None:
        if breaking_index != trailer_index - 2:
            raise BatchPlanError(
                "BREAKING CHANGE footer must be separated from the AI-Co-Authored-By trailer by a blank line"
            )
        if breaking_index == 0 or lines[breaking_index - 1] != "":
            raise BatchPlanError(
                "commit message must contain a blank line before the footer block"
            )
        if lines[breaking_index + 1] != "":
            raise BatchPlanError(
                "commit message must contain a blank line between BREAKING CHANGE and AI-Co-Authored-By"
            )
    elif trailer_index == 0 or lines[trailer_index - 1] != "":
        raise BatchPlanError(
            "commit message must contain a blank line before the trailer"
        )

    if trailer_index != len(lines) - 1:
        raise BatchPlanError("AI-Co-Authored-By trailer must be the last line")
