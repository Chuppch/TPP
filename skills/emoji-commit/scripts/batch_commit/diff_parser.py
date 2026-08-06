from __future__ import annotations

import hashlib
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any

from batch_commit.constants import HUNK_HEADER_PATTERN
from batch_commit.errors import BatchPlanError
from batch_commit.git_utils import run_git


def trim_path_label(label: str | None) -> str | None:
    """把 diff 头里的 a/、b/ 或 /dev/null 标记收敛成真实路径。"""
    if not label:
        return None
    if label == "/dev/null":
        return None
    if label.startswith(("a/", "b/")):
        return label[2:]
    return label



def parse_diff_git_paths(header_line: str) -> tuple[str | None, str | None]:
    """解析 `diff --git` 头，拿到旧路径和新路径。

    Example:
        parse_diff_git_paths("diff --git a/app.py b/app.py")
        # => ("app.py", "app.py")
    """
    if not header_line.startswith("diff --git "):
        raise BatchPlanError(f"unsupported diff header: {header_line}")

    parts = shlex.split(header_line[len("diff --git ") :])
    if len(parts) < 2:
        raise BatchPlanError(f"unable to parse diff header: {header_line}")

    return trim_path_label(parts[0]), trim_path_label(parts[1])



def stable_id(kind: str, path: str, patch: str) -> str:
    """基于 kind、path 和 patch 内容生成稳定 unit id。"""
    payload = f"{kind}\0{path}\0".encode("utf-8") + patch.encode("utf-8")
    return f"{kind}-{hashlib.sha256(payload).hexdigest()[:12]}"



def detect_change_type(lines: list[str]) -> str:
    """从单个文件 patch 头部推断 Git 变更类型。"""
    stripped_lines = [line.rstrip("\n") for line in lines]
    if any(line.startswith("new file mode ") for line in stripped_lines):
        return "A"
    if any(line.startswith("deleted file mode ") for line in stripped_lines):
        return "D"
    if any(line.startswith("rename from ") for line in stripped_lines):
        return "R"
    return "M"



def parse_hunk_header(header_line: str) -> tuple[int, int, int, int]:
    """解析 hunk 头中的旧文件/新文件起始行与行数。"""
    match = HUNK_HEADER_PATTERN.match(header_line.strip())
    if not match:
        raise BatchPlanError(f"invalid hunk header: {header_line}")

    old_count = int(match.group("old_count") or "1")
    new_count = int(match.group("new_count") or "1")
    return (
        int(match.group("old_start")),
        old_count,
        int(match.group("new_start")),
        new_count,
    )



def split_patch_blocks(diff_text: str) -> list[str]:
    """把整段 diff 文本按文件切成独立 patch block。

    Example:
        blocks = split_patch_blocks(run_git(repo_path, ["diff", "--binary"]))
    """
    if not diff_text.strip():
        return []

    blocks: list[str] = []
    current: list[str] = []

    for line in diff_text.splitlines(keepends=True):
        # Git 会把多个文件 patch 串成一段输出，这里先切回单文件 block，
        # 后面的覆盖率校验和 unit 分配才能按文件精确判断。
        if line.startswith("diff --git "):
            if current:
                blocks.append("".join(current))
            current = [line]
            continue

        if current:
            current.append(line)

    if current:
        blocks.append("".join(current))

    return blocks



def build_untracked_patch_blocks(
    repo_path: str | Path,
    base_head: str,
    untracked_paths: list[str],
) -> list[str]:
    """在临时 index 中 stage 未跟踪路径，并导出稳定的新增 patch block。

    Example:
        blocks = build_untracked_patch_blocks(repo_path, base_head, ["new.txt"])
    """
    paths = sorted(filter(None, untracked_paths))
    if not paths:
        return []

    with tempfile.TemporaryDirectory(prefix="emoji-commit-untracked-index-") as temp_dir:
        temp_index = Path(temp_dir) / "index"
        env = {"GIT_INDEX_FILE": str(temp_index)}
        # `git diff HEAD` 无法包含 untracked 内容，这里用隔离 index 暂存它们，
        # 再通过 `git diff --cached <base>` 导出成标准新增 patch。
        run_git(repo_path, ["read-tree", base_head], env=env)
        run_git(repo_path, ["add", "--all", "--", *paths], env=env)
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
                base_head,
                "--",
                *paths,
            ],
            env=env,
        )

    return split_patch_blocks(diff_text)



def change_type_summary(
    change_type: str,
    *,
    binary: bool = False,
    old_path: str | None = None,
    new_path: str | None = None,
) -> str:
    """把 Git 变更类型转成更适合预览文本的摘要。"""
    if binary:
        return "binary patch"
    if change_type == "A":
        return "new file"
    if change_type == "D":
        return "delete file"
    if change_type == "R":
        return f"rename {old_path} -> {new_path}"
    return "file patch"



def diff_is_whitespace_only(unit_patches: list[str]) -> bool:
    """基于 patch 行判断本次文本变更是否只包含空白差异。"""
    removed: list[str] = []
    added: list[str] = []
    for patch in unit_patches:
        if "GIT binary patch" in patch or "Binary files " in patch:
            return False
        for line in patch.splitlines():
            if not line or line.startswith(
                (
                    "+++",
                    "---",
                    "@@",
                    "diff --git ",
                    "index ",
                    "new file mode ",
                    "deleted file mode ",
                )
            ):
                continue
            if line.startswith(
                ("rename from ", "rename to ", "similarity index ", "old mode ", "new mode ")
            ):
                continue
            if line.startswith("+"):
                added.append(re.sub(r"\s+", "", line[1:]))
                continue
            if line.startswith("-"):
                removed.append(re.sub(r"\s+", "", line[1:]))
                continue

    return bool(added or removed) and added == removed



def parse_file_patch(block: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """把单文件 patch 解析成 file record 与可分配的 units。

    Example:
        file_record, units = parse_file_patch(patch_block)
    """
    if not block.strip():
        raise BatchPlanError("encountered empty diff block")

    lines = block.splitlines(keepends=True)
    old_path, new_path = parse_diff_git_paths(lines[0].rstrip("\n"))
    change_type = detect_change_type(lines)
    binary = "GIT binary patch" in block or any(
        line.startswith("Binary files ") for line in lines
    )

    rename_from = None
    rename_to = None
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.startswith("rename from "):
            rename_from = stripped[len("rename from ") :]
        elif stripped.startswith("rename to "):
            rename_to = stripped[len("rename to ") :]

    if rename_from:
        old_path = rename_from
    if rename_to:
        new_path = rename_to

    path = new_path if change_type != "D" else old_path
    if not path:
        path = new_path or old_path
    if not path:
        raise BatchPlanError(f"unable to resolve patch path: {lines[0].rstrip()}")

    hunk_indices = [
        index for index, line in enumerate(lines) if line.startswith("@@ ")
    ]
    header_lines = lines[: hunk_indices[0]] if hunk_indices else lines[:]

    # 只有“普通文本修改 + 多个互不重叠的 hunk”才允许按 hunk 拆分。
    # 新增、删除、重命名、二进制 patch 都保持 file 级，避免生成 Git
    # 无法安全重放的半成品状态。
    partial_split_supported = (
        change_type == "M"
        and not binary
        and len(hunk_indices) > 1
        and old_path == new_path
    )

    units: list[dict[str, Any]] = []

    if binary or change_type in {"A", "D", "R"} or not hunk_indices:
        patch = block if block.endswith("\n") else f"{block}\n"
        units.append(
            {
                "id": stable_id("file", path, patch),
                "kind": "file",
                "path": path,
                "change_type": change_type,
                "patch": patch,
                "summary": change_type_summary(
                    change_type,
                    binary=binary,
                    old_path=old_path,
                    new_path=new_path,
                ),
                "partial_split_supported": False,
                "binary": binary,
            }
        )
    else:
        slice_boundaries = hunk_indices + [len(lines)]
        for start, end in zip(slice_boundaries, slice_boundaries[1:]):
            hunk_lines = lines[start:end]
            hunk_header = hunk_lines[0].rstrip("\n")
            old_start, old_count, new_start, new_count = parse_hunk_header(hunk_header)
            patch = "".join(header_lines + hunk_lines)
            units.append(
                {
                    "id": stable_id("hunk", path, patch),
                    "kind": "hunk",
                    "path": path,
                    "change_type": change_type,
                    "patch": patch,
                    "summary": hunk_header,
                    "partial_split_supported": partial_split_supported,
                    "old_start": old_start,
                    "old_count": old_count,
                    "new_start": new_start,
                    "new_count": new_count,
                }
            )

    file_record = {
        "path": path,
        "old_path": old_path or path,
        "new_path": new_path or path,
        "change_type": change_type,
        "binary": binary,
        "partial_split_supported": partial_split_supported,
        "unit_ids": [unit["id"] for unit in units],
    }

    return file_record, units
