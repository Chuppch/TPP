# emoji-commit

生成规范化提交信息，支持分析已暂存变更，或将整个未提交工作树拆分成可预览、可确认、可事务式应用的 commit 批次。

## 安装

```bash
npx -y @meitu/skills add git@git.meitu.com:fex/internal-skills.git --skill emoji-commit
```

使用 `npx @meitu/skills` 脚本前，需确保全局 `.npmrc` 包含以下配置：

```bash
npmrc="$HOME/.npmrc"; block=$'@meitu:registry=http://npm.meitu-int.com\nregistry=https://registry.npmmirror.com'; grep -Fqx "$block" "$npmrc" 2>/dev/null || printf '%s\n' "$block" >> "$npmrc"
```

详细配置说明参考 [`.npmrc` 配置说明](https://cf.meitu.com/confluence/x/XTuOEg)。

## 技能配置

`emoji-commit` 会从目标 Git 仓库根目录读取 `.agents/fex-skills.config.json`。该文件用于团队共享配置，可以提交到项目仓库。

例如配置提交描述语言：

```json
{
  "emoji-commit": {
    "language": "zh"
  }
}
```

`emoji-commit.language` 支持：

- `en`：英文，默认值。
- `zh`：简体中文。

语言优先级为：用户本轮明确要求中文或英文 > `.agents/fex-skills.config.local.json` > `.agents/fex-skills.config.json` > 默认 `en`。如果没有任何配置，即使用户用中文交流，提交描述也应使用英文。

如果只想在本地覆盖团队配置，可以创建 `.agents/fex-skills.config.local.json`。本地配置会递归合并到项目配置之上，同名字段优先使用本地配置值。

```json
{
  "emoji-commit": {
    "language": "en"
  }
}
```

本地配置必须加入 `.gitignore`。如果 `.agents/fex-skills.config.local.json` 存在但未被 Git 忽略，`emoji-commit` 会将其视为门禁失败并阻断提交流程。

推荐写法：

```gitignore
.agents/fex-skills.config.local.json
```

如果项目希望统一忽略所有本地 agent 配置，也可以使用：

```gitignore
.agents/*.local.json
```

## 提交消息语言范围

语言配置只影响人类描述文本：

- 标题描述
- 正文条目
- `BREAKING CHANGE:` 后的描述文本

以下协议字段始终保持英文和既有语法：

- `:emoji:` shortcode
- `(scope)`
- `!`
- `Jira-Refs:`
- `BREAKING CHANGE:`
- `AI-Co-Authored-By:`

以下上下文不会自动覆盖语言配置：

- 用户当前对话使用中文
- 仓库要求 Markdown 或 OpenSpec 文档使用中文
- 本次改动主要是中文文档

## Batch skill 包快照识别

批量提交分析 `.agents/skills/*` 变更时，会识别这些文件是否更像项目仓库中同步/安装的 skill 包快照，而不是业务代码。

被识别为 repo skill package snapshot 的变更，preview 默认建议聚合为一条 `(skills)` scope 提交：

- 英文：`:sparkles: (skills) update repo skill packages`
- 中文：`:sparkles: (skills) 更新项目技能`

如果 skill 包快照和业务代码同时存在，preview 会建议分开提交。若检测到 whitespace-only、frontmatter 名称不一致或 lock/source 漂移等信号，preview 会标注为 suspicious/noise，供确认后再提交。

## 文档

- [SKILL.md](./SKILL.md)：运行时入口、默认路由和硬结果约束。
- [references/single-commit.md](./references/single-commit.md)：单次提交流程。
- [references/batch-commit.md](./references/batch-commit.md)：批量提交流程。
- [references/fex-conventional-commits.md](./references/fex-conventional-commits.md)：FEX emoji-first 提交约定。
- [references/cz-emoji-types.md](./references/cz-emoji-types.md)：emoji 类型表。
- [references/troubleshooting.md](./references/troubleshooting.md)：异常处理与恢复。

## License

[WTFPL](../../LICENSE)
