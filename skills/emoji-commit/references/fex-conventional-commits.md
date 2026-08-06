# FEX 提交约定（emoji-first）

这是前端技术部内部给 `emoji-commit` 用的一套提交约定。

它参考 [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) 的语义、结构和写法，但不直接照搬 `type(scope): subject` 这一套标题形式。对我们来说，更重要的是保留 emoji-first 的使用习惯，同时把 `type`、`scope`、`breaking change` 和 footer 这些核心语义收拢到一套稳定规则里。

除非另有说明，本文中的“提交消息”都指 `emoji-commit` 生成或定稿后的最终提交内容。

## 这份文档负责什么

这份文档只描述**最终提交消息必须满足的规范结果**：

- 标题骨架是什么
- footer 顺序是什么
- `Jira-Refs:`、`BREAKING CHANGE:` 和 `AI-Co-Authored-By:` 如何共存

下面这些内容不属于本规范真源：

- `Subject` 要不要控制在某个字符数以内
- 是否使用祈使语气、英文描述等写作偏好
- `printf + --file`、heredoc、多 `-m` 等 shell 执行方式
- hook 故障排查、自检失败恢复等执行细节

这些内容请按需读取：

- `single-commit.md`
- `batch-commit.md`
- `troubleshooting.md`

## 摘要

这套约定的核心很简单：

- 标题仍然以 shortcode emoji 开头
- emoji 负责表达 Conventional Commits 的 `type` 语义
- `scope` 可以写，也可以不写
- Jira 引用通过 `Jira-Refs:` footer 表达
- 破坏性变更通过独立的 `!` 和 `BREAKING CHANGE:` 来表达
- `AI-Co-Authored-By` 继续保留，而且必须放在最后
- 提交描述语言可由 FEX skills 配置决定，但协议字段保持英文

换句话说，我们不是把 Conventional Commits 原样搬进来，而是把它的核心语义翻译成更适合 FEX 日常使用的写法。

本文保留以下语义能力：

- `type`：由 emoji 表达
- `scope`：可选
- `jira refs`：由 `Jira-Refs:` footer 表达
- `breaking change`：由独立 `!` 标记和 `BREAKING CHANGE:` footer 表达
- `footer`：支持标准 breaking footer，并继续强制 `AI-Co-Authored-By`

## 语言偏好

`emoji-commit` 可通过 FEX skills 项目配置读取提交描述语言偏好：

```json
{
  "emoji-commit": {
    "language": "zh"
  }
}
```

支持值：

- `en`：英文，默认值。
- `zh`：简体中文。

语言优先级为：用户本轮明确要求中文或英文 > `.agents/fex-skills.config.local.json` > `.agents/fex-skills.config.json` > 默认 `en`。没有配置时，即使用户用中文交流、仓库 Markdown 要中文、OpenSpec 文档要中文，提交描述也仍然使用英文。

语言偏好只影响人类描述文本：

- header subject
- body bullet 内容
- `BREAKING CHANGE:` 后的描述文本

语言偏好不改变协议字段：

- `:emoji:` shortcode
- `(scope)`
- `!`
- `Jira-Refs:`
- `BREAKING CHANGE:`
- `AI-Co-Authored-By:`

反例：

```text
用户输入：
先提交代码吧

仓库配置：
无 `.agents/fex-skills.config.json`
无 `.agents/fex-skills.config.local.json`

错误：
:memo: 更新 emoji-commit 语言规则

正确：
:memo: update emoji-commit language rules
```

## 提交消息结构

提交消息按下面的结构组织：

```text
:emoji: subject
:emoji: ! subject
:emoji: (scope) subject
:emoji: (scope) ! subject

[optional body]

[optional footer(s)]
Jira-Refs: <KEY>[, <KEY>...]

BREAKING CHANGE: <description>

AI-Co-Authored-By: <AGENT_NAME>
```

## 硬约束

1. 提交标题必须以前导 emoji 开头，且该 emoji 必须使用 shortcode 形式（例如 `:bug:`、`:sparkles:`），不得使用 Unicode emoji。
2. 前导 emoji 表示 Conventional Commits 的 `type` 语义。
3. `scope` 是可选项；当存在时，必须写成 `(scope)`。
4. `!` 是独立的 breaking change 标记；当存在时，必须位于 emoji 或 `(scope)` 之后、subject 之前，并与两侧保持空格分隔。
5. body 是可选项；当存在时，继续使用 bullet 风格，并保持简洁。
6. `Jira-Refs:` 是可选 footer；当存在时，必须使用单行聚合格式 `Jira-Refs: KEY1, KEY2`。
7. `Jira-Refs:` 中的 Jira Key MUST 去重，并保持首次出现顺序。
8. `Jira-Refs:` MUST NOT 为 Jira Key 添加 `#`。
9. `BREAKING CHANGE:` 是可选 footer；当存在时，用于补充说明 breaking change 的具体影响。
10. 当 `Jira-Refs:` 与 `BREAKING CHANGE:` 同时存在时，两者之间必须保留一个空行。
11. 当 `Jira-Refs:` 存在但 `BREAKING CHANGE:` 不存在时，`Jira-Refs:` 与 `AI-Co-Authored-By:` 之间必须保留一个空行。
12. `BREAKING CHANGE:` 与 `AI-Co-Authored-By:` 之间必须保留一个空行。
13. `AI-Co-Authored-By:` 是必需 footer，且必须是提交消息的最后一行。
14. 仍然禁止 `Co-authored-by` / `Co-Authored-By` 等其他自动 co-author trailer 形式。
15. `emoji-commit.language` 为 `zh` 时，标题描述、正文条目和 `BREAKING CHANGE:` 描述文本使用简体中文；协议字段名仍保持英文。

## 示例

### 普通提交

```text
:bug: reject duplicate units
```

### 带 scope 的提交

```text
:sparkles: (emoji-commit) add conventional commit semantics
```

### breaking change 标题

```text
:bug: ! reject duplicate units
```

### 带 scope 的 breaking change 标题

```text
:sparkles: (emoji-commit) ! change header grammar
```

### 带 body 与 breaking footer 的完整提交

```text
:bug: ! reject duplicate units

- 早期拒绝重复单位分配
- 保持批量应用的事务性

Jira-Refs: DATA-6755, TECHPUB-19087

BREAKING CHANGE: 重复单位分配现在会更早被拒绝

AI-Co-Authored-By: Codex
```

### 中文描述提交

```text
:sparkles: (emoji-commit) 支持 FEX skills 语言配置

- 读取项目配置和本地覆盖配置
- 根据语言偏好生成中文提交描述

AI-Co-Authored-By: Codex
```

### 带 Jira-Refs 的完整提交

```text
:memo: (emoji-commit) document jira refs footer behavior

- 说明 `Jira-Refs:`、`BREAKING CHANGE:` 与 `AI-Co-Authored-By:` 的顺序

Jira-Refs: INTERNAL-1901, DATA-6755

AI-Co-Authored-By: Codex
```

### 从中文自然输入提取 Jira-Refs

```text
用户输入：
修复了 https://jira.meitu.com/browse/DATA-6755 https://jira.meitu.com/browse/TECHPUB-19087 这两个单子，你提交代码一下

期望 footer：
Jira-Refs: DATA-6755, TECHPUB-19087

AI-Co-Authored-By: Codex
```

## 类型映射

这里沿用 `emoji-commit` 已有的 emoji 语义，再把它们对齐到 Conventional Commits 的 `type` 概念。下面是推荐优先使用的核心映射：

| Emoji | Shortcode | Conventional 语义 | 说明 |
|---|---|---|---|
| ✨ | `:sparkles:` | `feat` | 新功能 |
| 🐛 | `:bug:` | `fix` | 修复缺陷 |
| 📝 | `:memo:` | `docs` | 文档更新 |
| ♻️ | `:recycle:` | `refactor` | 重构 |
| ⚡️ | `:zap:` | `perf` | 性能优化 |
| ✅ | `:white_check_mark:` | `test` | 测试变更 |
| 🔧 | `:wrench:` | `chore` | 配置或维护性变更 |
| 🚚 | `:truck:` | `chore` | 移动或重命名 |

更完整的 emoji 列表和语义说明，继续看 [cz-emoji-types.md](./cz-emoji-types.md)。

## 与 Conventional Commits 的关系

这份文档参考 [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) 的语义模型，但不直接采用它原生的 `type(scope): subject` 标题格式。

两者的对应关系大致如下：

- `type`：由 emoji 表达，而不是文字 token
- `scope`：继续保留 `(scope)` 结构，但为可选项
- `Jira-Refs:`：用于表达 Jira issue 引用，并为其他来源系统保留命名空间扩展空间
- `!`：保留为 breaking change 标记
- `BREAKING CHANGE:`：保留为 breaking footer
- `AI-Co-Authored-By:`：作为 FEX 额外增加的强制尾注规则

## Footer 顺序

当提交消息同时包含 body、`Jira-Refs:`、`BREAKING CHANGE:` 和 `AI-Co-Authored-By:` 时，顺序按下面来：

```text
:emoji: (scope) ! subject

- body item 1
- body item 2

Jira-Refs: <KEY>[, <KEY>...]

BREAKING CHANGE: <description>

AI-Co-Authored-By: <AGENT_NAME>
```

这里有五个硬约束：

- body 与 footer 之间必须保留一个空行
- `Jira-Refs:` 若存在，必须位于 `BREAKING CHANGE:` 之前
- `Jira-Refs:` 中必须使用单行聚合格式，多个 key 之间用 `, ` 分隔
- `Jira-Refs:` 与 `BREAKING CHANGE:` 之间必须保留一个空行；若没有 `BREAKING CHANGE:`，则与 `AI-Co-Authored-By:` 之间保留一个空行
- `BREAKING CHANGE:` 若存在，必须出现在 `AI-Co-Authored-By:` 之前
- `BREAKING CHANGE:` 与 `AI-Co-Authored-By:` 之间必须再保留一个空行
- `AI-Co-Authored-By:` 必须是最后一行

## 参考

- 上游规范：[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- 类型参考：[cz-emoji-types.md](./cz-emoji-types.md)
