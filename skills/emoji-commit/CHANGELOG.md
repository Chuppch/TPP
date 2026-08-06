# 更新文档

## 2026-06-14

- :sparkles: 支持识别项目技能快照，建议分组并标注同步噪音 (_郑少鹏_)
- :recycle: 拆分 batch commit 执行器模块，补充注释并保留兼容 (_郑少鹏_)

## 2026-06-08

- :bug: 修复 batch apply 绕过 `pre-commit` 的问题，改为逐条在隔离 worktree 中运行 hook，并吸收当前批次边界内的自动修正 (_郑少鹏_)

## 2026-06-04

- :memo: 强化提交语言门禁，要求 single / batch 提交前显式解析 `emoji-commit.language`，避免将中文对话或 Markdown 约束误判为中文提交描述 (_郑少鹏_)

## 2026-05-27

- :sparkles: 新增 FEX skills 配置读取与本地配置门禁，支持通过 `emoji-commit.language` 切换英文或简体中文提交描述 (_郑少鹏_)
- :memo: 新增技能配置 README，并同步 single、batch 与提交约定文档中的语言边界和 `.local` 忽略要求 (_郑少鹏_)

## 2026-05-08

- :sparkles: 新增 `Jira-Refs:` footer 规则，支持从 Jira URL / Key 聚合提取单行引用，并同步脚本校验与测试覆盖 (_郑少鹏_)
- :recycle: 将技能主文档重构为渐进式披露入口，拆出 single、batch 与 troubleshooting 按需参考，并同步 OpenSpec 规范与校验说明 (_郑少鹏_)

## 2026-05-07

- :sparkles: 新增 Fex Conventional Commits 约定，统一 `!`、`BREAKING CHANGE:` 与 `AI-Co-Authored-By` 的写法 (_郑少鹏_)

## 2026-04-29

- :bug: 修复 `worktree` inventory 对未跟踪文件与 symlink 的收集方式，避免批次计划漏收新增路径 (_郑少鹏_)
- :wrench: 兼容 `commit_batches.py` 在子命令前后传入 `--repo`，统一批次命令调用体验 (_郑少鹏_)
- :memo: 收紧单次与分批提交的选择规则，并补充真实 hook / lint-staged 配置优先的排查说明 (_郑少鹏_)

## 2026-04-24

- :sparkles: 新增批次提交工作流，支持分析整个未提交工作树并按计划拆成多条 commit (_郑少鹏_)
- :wrench: 补回 `commit_batches.py` 与测试，提供 `inventory`、`preview-plan`、`apply-plan` 的事务式批次能力 (_郑少鹏_)
- :memo: 更新技能说明与仓库路由文案，显式覆盖“分类未提交代码并分批提交”的触发场景 (_郑少鹏_)

## 2026-03-25

- :memo: 强化 `AI-Co-Authored-By` 规则为强制门禁，提交信息缺失该 trailer 视为不合规 (_郑少鹏_)
- :memo: 新增提交后校验命令，要求 `AI-Co-Authored-By` 恰好存在一行，并补充缺失/多行时的回滚重提指引 (_郑少鹏_)

## 2026-03-24

- :memo: 统一 Header 示例为 shortcode 形式，并新增 Header shortcode 合规自检指引 (_郑少鹏_)
- :memo: 调整文档顺序，将 AI-Co-Authored-By 规则置于 Shell 提交指令之前 (_陈珺_)
- :memo: 扩充 AGENT_NAME 解析、规范化与去重行为说明 (_陈珺_)
- :memo: 新增 Made-with 检测与 IDE 归因故障排查 (_陈珺_)
- :memo: 统一示例占位符格式，重新编号至提交后校验步骤 (_陈珺_)

## 2026-03-23

- :memo: 补全 `npx -y @meitu/skills add ...` 后缺失的代码块结束符 (_郑少鹏_)
- :memo: 新增 `AI-Co-Authored-By` 专用规则，明确为唯一允许的自动 trailer，且固定在消息末尾追加 (_郑少鹏_)
- :memo: 增加 `agent_name` 自动识别优先级（通用变量 -> 供应商提示 -> 兜底）及安全规范化约束 (_郑少鹏_)
- :memo: 增加 trailer 去重规则：已存在 `AI-Co-Authored-By:` 时跳过追加 (_郑少鹏_)
- :memo: 补充多来源 `agent_name` 追加示例，并统一与既有提交格式/非交互提交指引的一致性 (_郑少鹏_)
- :wrench: 收敛禁令措辞，继续禁止 `Co-authored-by` / `Co-Authored-By`，仅保留 `AI-Co-Authored-By` 特例 (_郑少鹏_)
- :wrench: 新增执行约束：默认使用 `printf` + `--file` 保障空行，提交后强制 raw 校验，失败时先 `git reset --soft HEAD~1` 再重提 (_郑少鹏_)

## 2026-03-06

- :memo: 统一 Commit Header 为 `:emoji: (scope) subject`，明确 emoji 后空格与去除 type 的约束 (_郑少鹏_)
- :memo: 收紧 Body 规则，限制 Long description 最多 5 条并要求合并同类描述 (_郑少鹏_)
- :memo: 将多行提交首选方案调整为 `cat <<'EOF' | git commit --file=-`，规避反引号与变量插值风险 (_郑少鹏_)
- :memo: 明确禁止输出任何 `Co-authored-by` / `Co-Authored-By` 行 (_郑少鹏_)

## 2026-03-03

- :wrench: 补充非交互式 Shell 场景下的换行处理说明，规避 `\\n` 字面量误用 (_郑少鹏_)
- :memo: 完善 commit 执行步骤，新增 `printf ... | git commit --file=-` 的多行提交推荐方案 (_郑少鹏_)
- :memo: 更新 lint-staged 故障排查，补充 npm/yarn/pnpm/bun 的命令示例 (_郑少鹏_)

## 2026-02-26

- :sparkles: 新增 `emoji-commit` 技能，定义 staged 变更分析、类型决策与提交格式流程 (_郑少鹏_)
- :memo: 新增 `references/cz-emoji-types.md`，补充 70+ cz-emoji 类型参考 (_郑少鹏_)
- :wrench: 增加项目级技能入口链接，便于多代理客户端加载 `emoji-commit` (_郑少鹏_)
