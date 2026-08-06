# Single Commit 详细流程

当你已经确定当前请求只需要提交 staged 改动，或用户明确要求“只提交暂存区”时读取本文。

## 1. 先确认当前确实是 single commit

```bash
git status --short
```

- 若只剩 staged 改动，继续本文。
- 若仍存在 unstaged 或 untracked 改动，默认改走 `batch-commit.md`。

## 2. 分析 staged 变更

```bash
git status
git diff --cached
git diff --cached --stat
```

始终根据实际改动生成 commit message，不要先写 message 再反推改动含义。

同时解析目标仓库中的 FEX skills 配置：

- `.agents/fex-skills.config.json` 是项目共享配置。
- `.agents/fex-skills.config.local.json` 是本地覆盖配置，并且必须被 Git 忽略。
- 如果本地配置存在但未被 `.gitignore` 覆盖，先停止提交，让用户加入忽略规则或移除本地配置。
- `emoji-commit.language` 支持 `en` 与 `zh`；默认 `en`，表示没有配置时提交描述使用英文。
- 语言优先级：用户本轮明确要求中文或英文 > `.local` 配置 > 项目配置 > 默认 `en`。
- 用户用中文交流、仓库 Markdown 要中文、OpenSpec 文档要中文，都不等于提交描述要中文。

固定 checkpoint：用现有 inventory 命令读取解析后的语言，并在生成 message 前记住它。

```bash
python3 <skill_root>/scripts/commit_batches.py \
  --repo <repo-path> \
  inventory \
  --scope staged > /tmp/emoji_commit_inventory.json

python3 -c 'import json; data=json.load(open("/tmp/emoji_commit_inventory.json")); print(data["config"]["emoji_commit_language"])'
```

若输出为 `en`，Subject 和 Body 必须使用英文，除非用户本轮明确要求中文 commit message。

## 3. 选择 emoji 和 header

完整标题/页脚规范看 `fex-conventional-commits.md`，完整 emoji 类型表看 `cz-emoji-types.md`。常用类型通常够用：

| Emoji | Shortcode | 语义 |
|---|---|---|
| ✨ | `:sparkles:` | 新功能 |
| 🐛 | `:bug:` | 修复 bug |
| ♻️ | `:recycle:` | 重构 |
| 💄 | `:lipstick:` | UI 更新 |
| 📝 | `:memo:` | 文档 |
| 🔧 | `:wrench:` | 配置 |
| ⚡️ | `:zap:` | 性能 |
| ✅ | `:white_check_mark:` | 测试 |
| 🚚 | `:truck:` | 移动 / 重命名 |
| 🔥 | `:fire:` | 删除代码或文件 |

允许的 header 骨架：

```text
:emoji: subject
:emoji: ! subject
:emoji: (scope) subject
:emoji: (scope) ! subject
```

## 4. 写 commit message

### 规范结果

- Header / footer 的硬约束统一服从 `fex-conventional-commits.md`。
- 若存在 Jira 上下文，生成单行 `Jira-Refs: KEY1, KEY2`。
- `AI-Co-Authored-By:` 必须且仅有一行，并且位于最后。

### 推荐写法

- 先确认已解析的 `emoji-commit.language`，再开始写 Subject 和 Body。
- 若语言偏好为 `en`，Subject 和 Body 用英文，尽量短而明确。
- 若语言偏好为 `zh`，Subject 和 Body 用简体中文，保持简洁自然。
- 尽量使用祈使语气，例如 `add` / `fix` / `document`。
- 合并重复描述，优先保留影响面最大的变更点。
- `BREAKING CHANGE:` 字段名始终保持英文；其后的描述文本按语言偏好生成。
- 当 Body 含反引号、多行内容或 footer 较多时，优先使用 `printf` + `--file`，不要把复杂内容塞进多个 `-m`。

### 当前脚本实现的限制

- 当前 `<skill_root>/scripts/commit_batches.py` 会拒绝超过 5 条 body items。
- 这更像当前执行器的实现级限制，而不是提交格式本身的唯一规范来源；如果内容过长，先合并再提交。

### 语言误判示例

```text
上下文：
- 用户用中文说“先提交代码吧”
- 仓库要求 OpenSpec Markdown 使用中文
- `.agents/fex-skills.config.json` 与 `.agents/fex-skills.config.local.json` 都不存在

解析结果：
emoji-commit.language=en

错误：
:sparkles: (util-cli) 新增 Agent 知识查询工具

正确：
:sparkles: (util-cli) add Agent knowledge query tool
```

## 5. 处理 Jira-Refs 和 AI trailer

### Jira-Refs

- 当用户消息、任务描述、分支名、暂存改动说明或当前上下文中出现 Jira URL 或 Jira Key 时，优先生成 `Jira-Refs:` footer。
- 去掉 URL 前缀，仅保留 Jira Key。
- 多个 Jira Key 合并到一行，使用 `, ` 分隔，保持首次出现顺序并去重。

中文自然输入示例：

```text
用户输入：
跟 DATA-6755、TECHPUB-19087 相关的改动已经好了，帮我提交

期望 footer：
Jira-Refs: DATA-6755, TECHPUB-19087

AI-Co-Authored-By: Codex
```

### AI-Co-Authored-By

最终提交信息必须包含且仅包含一行自动 trailer：`AI-Co-Authored-By: <AGENT_NAME>`。

`AGENT_NAME` 的自动识别优先级：

1. `COMMIT_AI_AGENT_NAME`
2. `AI_AGENT_NAME`
3. `AGENT_NAME`
4. 供应商 / 运行时前缀：
   - `OPENAI_` / `CODEX_` → `Codex`
   - `ANTHROPIC_` / `CLAUDE_` → `Claude`
   - `MINMAX_` → `MinMax`
   - `GOOGLE_` / `GEMINI_` → `Gemini`
5. 无可识别信号时，兜底为 `AI Agent`

规范化要求：

- trim 首尾空白
- 移除换行和控制字符，保证最终值为单行
- 若出现可能破坏 trailer 语义的额外冒号等分隔符，做最小安全清洗

## 6. 执行提交

### 推荐：`printf` + `--file`

在部分代理执行通道中，管道或 heredoc 可能压缩空行；如果你需要稳定保留 footer 空行，优先用文件方式提交：

```bash
printf '%s\n' \
":emoji: (scope) ! subject" \
'' \
'- Change 1' \
'- Change 2' \
'' \
'Jira-Refs: INTERNAL-1901, DATA-6755' \
'' \
'BREAKING CHANGE: <description>' \
'' \
'AI-Co-Authored-By: <AGENT_NAME>' > /tmp/commit_msg.txt

git commit --file /tmp/commit_msg.txt
```

### 备选 1：heredoc

```bash
cat <<'EOF' | git commit --file=-
:emoji: (scope) ! subject

- Change 1
- Change 2

Jira-Refs: INTERNAL-1901, DATA-6755

BREAKING CHANGE: <description>

AI-Co-Authored-By: <AGENT_NAME>
EOF
```

### 备选 2：多个 `-m`

```bash
git commit -m ':emoji: (scope) ! subject' -m "- Change 1
- Change 2" -m "Jira-Refs: INTERNAL-1901, DATA-6755" -m "" -m "BREAKING CHANGE: <description>" -m "" -m "AI-Co-Authored-By: <AGENT_NAME>"
```

当 Body 含反引号时，优先使用推荐方案而不是把复杂内容塞进双引号字符串。

## 7. 提交后自检

先检查正文和 footer 的空行：

```bash
git cat-file -p HEAD | sed -n '/^$/,$p' | sed -n '2,120p' | cat -vet
```

再校验 Header shortcode：

```bash
git log -1 --pretty=%B | head -n 1 | grep -Eq '^:[a-z0-9_+-]+:( \([^)]+\))?( !)? .+'
```

再校验 trailer 恰好一行：

```bash
git log -1 --pretty=%B | grep -Eic '^AI-Co-Authored-By:[[:space:]].+$' | grep -qx '1'
```

最后按提交前解析出的 `emoji-commit.language` 做语言核对：若语言为 `en`，但最新提交的 Subject 或 Body 明显使用中文，立即 `git commit --amend` 修正为英文；若语言为 `zh`，则反向检查是否误用了英文描述。

如果自检失败，直接转到 `troubleshooting.md`，那里包含缺空行、缺 trailer、`Made-with:` 噪音和 hook 失败时的恢复动作。
