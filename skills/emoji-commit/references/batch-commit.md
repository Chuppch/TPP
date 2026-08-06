# Batch Commit 详细流程

当用户希望“先看整个未提交工作树，再按逻辑拆成多条 commit”，或当前仍存在 unstaged / untracked 改动时读取本文。

## 适用场景

以下表达默认进入 batch commit，而不是只盯着 staged diff：

- “看看 git 里没提交的代码，分类一下，然后分批提交代码”
- “把这些改动拆成几次 commit”
- “按逻辑分批提交”
- `split commits`
- `batch commit`

默认输入范围是整个未提交工作树（`worktree`），包含：

- 已暂存变更
- 未暂存变更
- 未跟踪文件

## 0. 先确认输入范围

```bash
git status --short
```

- 只要存在 unstaged 或 untracked 改动，默认用 `--scope worktree`。
- 只有工作区除 staged 外已经干净，或用户明确要求“只提交暂存区”，才用 `--scope staged`。
- 若遇到未跟踪 symlink / 目录被旧版 inventory 漏收，修复动作见 `troubleshooting.md`。

执行器会先读取 FEX skills 配置，并执行本地配置门禁：

- 项目配置：`.agents/fex-skills.config.json`。
- 本地覆盖：`.agents/fex-skills.config.local.json`。
- 两者按对象递归合并，同名字段优先使用本地值。
- 本地配置存在时必须被 Git 忽略；未忽略或已进入 index 时，`inventory` / `preview-plan` / `apply-plan` 都会失败。
- `emoji-commit.language` 支持 `en` 与 `zh`，默认 `en`；生成计划时按已解析语言写 `message.header`、`message.body` 和 `message.breaking_change`。
- 用户用中文交流、仓库 Markdown 要中文、OpenSpec 文档要中文，都不改变 inventory 里的语言解析结果。

## 1. 收集 inventory

使用 `<skill_root>/scripts/commit_batches.py` 输出当前工作树 inventory：

```bash
python3 <skill_root>/scripts/commit_batches.py \
  --repo <repo-path> \
  inventory \
  --scope worktree > /tmp/emoji_commit_inventory.json
```

输出 JSON 至少包含：

- `base_ref`
- `base_head`
- `input_scope`
- `files`
- `units`
- `stats`
- `config.emoji_commit_language`
- `config.warnings`

### Repo skill package snapshot

当 inventory 命中 `.agents/skills/<skill-name>/**` 时，执行器会尝试补充领域语义字段：

- `domain=agent-skill`
- `skill_name=<skill-name>`
- `skill_root=.agents/skills/<skill-name>`
- `skill_origin`
- `recommended_group`
- `warnings`

`skill_origin` 可能为：

- `external-lock-managed`：`skills-lock.json` 记录了该 skill 的 `sourceUrl` / `sourceType` / `computedHash` / `skillPath` 等来源信息。
- `repo-installed-skill`：`.agents/skills/<skill-name>/SKILL.md` 存在，且未确认它是当前仓库 `skills/<skill-name>` 的源目录镜像。
- `source-symlink`：`.agents/skills/<skill-name>` 是指向 `skills/<skill-name>` 的 symlink，通常表示源仓库内的 runtime 镜像。
- `ambiguous-skill-dir`：具备 skill 包结构，但现有信号不足以确认来源。

若相关文件带有 `recommended_group=repo-skill-packages`，默认把它们视为项目仓库中的 skill 包快照，而不是业务代码。生成计划时优先聚合为一条 `(skills)` scope commit：

- `emoji-commit.language=en`：`:sparkles: (skills) update repo skill packages`
- `emoji-commit.language=zh`：`:sparkles: (skills) 更新项目技能`

若 repo skill package snapshot 与业务代码同时存在，默认生成独立提交，不要把 `.agents/skills/*` 和业务文件混进同一 commit。

`warnings` 只用于提示风险，不默认丢弃变更：

- `whitespace-only`：该 skill 文件 diff 忽略空白后为空，可能是格式噪音。
- `suspicious-frontmatter`：`SKILL.md` frontmatter `name` 与路径名不一致。
- `suspicious-lock-drift`：存在 lock 来源记录，但实际 skill 结构疑似漂移。
- `suspicious-installed-copy`：当前仓库有匹配的 `skills/<skill-name>` 源目录，但 `.agents/skills/<skill-name>` 不是指向它的 symlink。
- `ambiguous-skill-dir`：来源语义不明确，需要用户确认。

## 2. 生成批次计划

根据 inventory 组织计划 JSON，固定结构如下：

```json
{
  "base_head": "<HEAD hash from inventory>",
  "input_scope": "worktree",
  "commits": [
    {
      "id": "commit-1",
      "reason": "why this batch exists",
      "split_mode": "file",
      "units": ["file-1234567890ab"],
      "message": {
        "header": ":wrench: (scope) subject",
        "body": ["bullet 1", "bullet 2"]
      }
    }
  ]
}
```

规则：

- `input_scope` 在 v1 默认写 `worktree`。
- 每个 `unit` 必须恰好归属一个 commit，禁止遗漏和重复。
- `split_mode=file` 表示该 commit 必须完整覆盖某个文件的全部 unit。
- `split_mode=hunk` 只允许用于 `partial_split_supported=true` 的文本 patch。
- `message.header`、`message.body`、`message.jira_refs` 继续服从主文档和 `fex-conventional-commits.md` 的约束。
- `message.header`、`message.body` 和 `message.breaking_change` 的描述文本应遵循 inventory 中的 `config.emoji_commit_language`。
- 计划文件建议写到仓库外部临时路径，例如 `/tmp/emoji_commit_plan.json`，避免把 plan 本身当成新的未跟踪改动。

## 3. 预览计划

不要直接 apply 多条 commit，先渲染预览：

```bash
python3 <skill_root>/scripts/commit_batches.py \
  --repo <repo-path> \
  preview-plan \
  --plan /tmp/emoji_commit_plan.json
```

预览时至少确认：

- 拆分边界是否合理
- 每条 commit 的 header / body 是否符合语义
- 每条 commit 的描述语言是否符合 inventory 中的 `config.emoji_commit_language`；例如该值为 `en` 时，不要因为用户中文输入而生成中文 subject/body
- 是否存在本应合并或本应拆开的改动
- 是否出现 repo skill package snapshot 提醒；若出现，优先确认是否应按 `(skills)` 聚合提交
- 是否出现 suspicious/noise 提醒；若出现，先确认是否需要清理同步噪音或去 skill 源仓库提交
- 是否触发本地配置门禁；门禁失败时先处理 `.gitignore`，不要继续 apply

## 4. 等待用户确认

batch commit 的默认边界是：

- 先展示 preview
- 等用户确认
- 再执行 apply

v1 默认不自动创建多条 commit。

## 5. 确认后 apply

```bash
python3 <skill_root>/scripts/commit_batches.py \
  --repo <repo-path> \
  apply-plan \
  --plan /tmp/emoji_commit_plan.json
```

`apply-plan` 的行为约束：

- 先校验 `base_head` 是否仍与 preview 时一致
- 再校验当前 inventory 与计划中的 unit 分配是否仍匹配
- 在隔离的 shadow worktree 中按计划顺序 materialize 每条 commit
- 每条计划 commit 创建前都会运行 `git hook run --ignore-missing pre-commit`
- hook 直接读取文件系统时，看到的是当前计划 commit 的工作区快照，而不是主工作区最终态
- hook 产生并 stage 的修改若仍限定在当前 commit 路径边界内，会被吸收到该 commit
- hook 修改当前 commit 边界外的 tracked 文件、创建边界外 untracked 文件，或留下 unstaged 修改时，`apply-plan` 失败
- `split_mode=hunk` 下，如果 hook 修改了同一文件，`apply-plan` 失败，需重新规划或改用 file split
- 所有 hook 验证通过后，再通过事务式 `update-ref` 落地主仓库提交链
- 成功后一次性更新 `HEAD` 与 index
- 失败时回滚 `HEAD` 与 index，不保留半成品提交
- `--scope worktree` apply 成功后，执行器会把计划覆盖路径的工作区内容同步到最终提交快照；`--scope staged` 不会主动改写工作区文件

## 6. 逐条提交后校验

apply 完成后，仍需对最终提交执行消息校验：

- Header shortcode 合规
- `AI-Co-Authored-By:` 恰好一行
- Header / Body / footer 的空行位置正确
- Header / Body / `BREAKING CHANGE:` 描述语言符合 inventory 中的 `config.emoji_commit_language`
- `Jira-Refs:` 若存在，必须保持单行聚合格式与正确顺序

如需具体自检命令，回看 `single-commit.md`；如遇 preview / apply 失败、范围判断错误或 inventory 边缘问题，转到 `troubleshooting.md`。
