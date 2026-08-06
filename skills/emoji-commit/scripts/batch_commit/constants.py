from __future__ import annotations

import re
from pathlib import Path


# 提交标题格式：shortcode emoji、可选 scope、可选破坏性标记。
HEADER_PATTERN = re.compile(r"^:[a-z0-9_+-]+:(?: \([^)]+\))?(?: !)? .+")

# 提交页脚格式：单行规范化的 BREAKING CHANGE 描述。
BREAKING_CHANGE_PATTERN = re.compile(r"^BREAKING CHANGE:[ \t].+$")

# 提交页脚格式：单行规范化的 Jira 引用列表。
JIRA_REFS_PATTERN = re.compile(r"^Jira-Refs:[ \t].+$")

# 提交页脚格式：必需的 AI 署名 trailer。
TRAILER_PATTERN = re.compile(r"^AI-Co-Authored-By:[ \t].+$", re.IGNORECASE)

# 禁用标准 co-author trailer；AI 署名只允许使用专用 trailer。
FORBIDDEN_COAUTHOR_PATTERN = re.compile(r"^Co-authored-by:|^Co-Authored-By:")

# 美图 Jira 浏览 URL 格式；捕获组是 issue key。
JIRA_URL_PATTERN = re.compile(r"https?://jira\.meitu\.com/browse/([A-Z][A-Z0-9]+-\d+)")

# Jira issue key 格式，用于直接 key 输入和混合文本提取。
JIRA_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")

# Git unified-diff hunk 头解析器，用于安全的 hunk 级拆分。
HUNK_HEADER_PATTERN = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)

# FEX skills 共享项目配置路径，从目标仓库根目录解析。
FEX_SKILLS_CONFIG_PATH = Path(".agents/fex-skills.config.json")

# FEX skills 本地覆盖配置路径，从目标仓库根目录解析。
FEX_SKILLS_LOCAL_CONFIG_PATH = Path(".agents/fex-skills.config.local.json")

# skill 包锁文件路径，用于判断已安装 skill 快照来源。
SKILLS_LOCK_PATH = Path("skills-lock.json")

# 目标仓库内已安装 agent skill 包的路径前缀。
AGENT_SKILLS_PREFIX = ".agents/skills/"

# repo skill package snapshot 变更的推荐分组标记。
REPO_SKILL_PACKAGES_GROUP = "repo-skill-packages"

# 项目配置缺失或无效时的默认提交描述语言。
DEFAULT_EMOJI_COMMIT_LANGUAGE = "en"

# emoji-commit 配置支持的提交描述语言集合。
SUPPORTED_EMOJI_COMMIT_LANGUAGES = {"en", "zh"}
