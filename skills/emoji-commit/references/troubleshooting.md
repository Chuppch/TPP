# Emoji Commit Troubleshooting

当你遇到自检失败、hook 失败、没有 staged 变更、`Made-with:` 噪音或 batch inventory 边缘问题时读取本文。

## 自检失败：空行或 footer 位置不对

若提交后发现 footer 空行丢失，或 `Jira-Refs:` / `BREAKING CHANGE:` / `AI-Co-Authored-By:` 顺序不对，先撤回最近一次提交：

```bash
git reset --soft HEAD~1
```

然后回到 `single-commit.md`，优先使用 `printf + --file` 重新提交。

## 自检失败：缺少或重复 `AI-Co-Authored-By`

若 trailer 缺失或出现多行，先撤回最近一次提交：

```bash
git reset --soft HEAD~1
```

然后重新生成最终 commit message，确保：

- 只有一行 `AI-Co-Authored-By: <AGENT_NAME>`
- 这行位于最后

## 出现 `Made-with: <IDE_NAME>`

若最终 commit message 被额外注入 `Made-with:` 行：

- 先询问用户是否希望保留该信息。
- 若不希望保留，提示用户关闭 IDE / Agent attribution 相关设置。
- 已生成的提交可用 `git commit --amend` 删除多余行；若已经进入历史，可按需要使用非交互式历史整理方式。

## 没有 staged 变更

若用户只是想提交一条 commit，先暂存目标文件：

```bash
git add <files>
```

若用户真正想“先分类整个未提交工作树，再拆成多条 commit”，不要停在这里只补 `git add`，而应回到 `batch-commit.md`，直接按整个 worktree 重新评估。

## `worktree` inventory 对未跟踪 symlink 或目录漏收

旧版本场景下，可先把当前工作树完整暂存，再改走 staged 范围重新规划：

```bash
git add -A
python3 <skill_root>/scripts/commit_batches.py \
  --repo <repo-path> \
  inventory \
  --scope staged > /tmp/emoji_commit_inventory.json
```

这属于保守 fallback，不是默认主路径。

## Hook 或 lint-staged 失败

不要假设每个仓库的 hook 都一样。优先检查真实配置：

1. `package.json` 里的 `scripts` 与 `lint-staged`
2. `.husky/pre-commit` 或仓库里的其他 Git hook

只运行仓库里确实存在的命令，不要默认假设 `lint`、`prettier`、`stylelint` 或 `pnpm run commit` 一定可用。

batch commit 的 `apply-plan` 会在隔离的 shadow worktree 中逐条运行 `pre-commit`：

- 若 hook 返回失败，先查看错误中标出的 commit id/header，再修复对应批次内容。
- 若 hook 自动格式化并 stage 当前批次路径内的文件，执行器会吸收这些修改。
- 若 hook 修改当前批次以外的路径、创建边界外 untracked 文件，或留下 unstaged 修改，执行器会阻断 apply。
- 若 hunk split 涉及的文件被 hook 改写，重新生成 inventory / preview，并优先把该文件改为 file split。
- 若 hook 修正导致后续 patch 无法应用，先手动运行格式化或调整计划，再重新 preview；不要在旧 plan 上强行 apply。

## 需要手工 fallback

仅在当前仓库已明确配置时，才把这些命令当作手工 fallback：

```bash
pnpm run commit
# 或
git cz
```
