# TPP 项目协作约定

本文件适用于整个 TPP 仓库。父目录 `../AGENTS.md` 中关于 macOS 纯 CPU、小规模实例、Section 2 复现边界和验证交付的要求继续有效。

## 项目定位与当前基线

- 本仓库是 Kapancioglu 与 Bernardino（2025）UTPP `ILS-RC` 的独立 Python 算法级复现，不是 SVRAP 子模块。
- 当前基线对应论文 Section 2 的 Algorithms 2–9，已包含构造解、五类邻域、Route Configuration、Local Search、Destroy/Repair、Diversity 重启和 ILS 主循环。
- 第一优先级是维持一份可验证的论文原始基线。神经网络、禁忌搜索、新邻域、增量缓存或性能优化如果后续加入，必须与基线分层、可关闭，并单独说明与论文的差异。
- 未获得作者原始代码。因此可以声称“根据论文伪代码完成算法级复现”，不得在未使用同一 benchmark、参数、种子、运行次数和统计方法时宣称完整复现论文实验表。

## 算法执行链路总览

整个 ILS-RC 求解的数据流和调用关系如下：

```text
输入：JSON 文件 → io.py 解析 → TPPInstance（不可变问题实例）
      命令行参数 → cli.py 解析 → ILSConfig（不可变算法配置）

求解：ils.py（总编排器）
      │
      ├── 初始阶段
      │     constructive_heuristic(instance) → 初始 Solution
      │     route_configuration(solution)    → 改进市场集合
      │     local_search(solution)           → 优化访问顺序
      │     → incumbent = 当前最优
      │
      └── 迭代循环（k_max 轮）
            │
            ├── 正常情况：destroy → repair → 扰动后的 Solution
            │   或
            ├── 僵局重启：diversity_constructive_heuristic → 全新 Solution
            │
            ├── route_configuration → 改进市场集合
            ├── local_search        → 优化访问顺序
            └── if 严格改进 → 更新 incumbent

输出：ILSResult（最优 Solution + 运行元数据）→ cli.py 格式化输出
```

### 模块角色定位

| 模块 | 角色 | 说明 |
|------|------|------|
| `domain/model.py` | 数据定义 | 四个不可变 dataclass：TPPInstance、Solution、ILSConfig、ILSResult |
| `domain/evaluation.py` | 工具函数集 | build_solution、travel_cost、is_strictly_better 等，被动调用 |
| `core/local_solution/constructive.py` | 初始解生成 | 贪心选市场 + 最近邻排路线，仅在 ILS 开始时调用一次 |
| `core/local_solution/neighborhoods.py` | 底层邻域能力 | 五种邻域生成器 + explore 引擎（best-improvement 搜索） |
| `core/local_solution/route_configuration.py` | 中层编排 | 按固定顺序编排 ADD/DROP/EXCHANGE 改变市场集合 |
| `core/local_solution/local_search.py` | 中层编排 | 三种序列编排 MOVE/SWITCH 优化访问顺序 |
| `core/ils_engine/perturbation.py` | 扰动机制 | destroy 删市场 + repair 补回来，跳出局部最优 |
| `core/ils_engine/diversity.py` | 多样性重启 | 利用共同出现记忆构造差异化新解 |
| `core/ils_engine/ils.py` | 顶层总编排 | 控制迭代、扰动/重启决策、incumbent 更新 |
| `exact.py` | 验证 oracle | 穷举真实最优解（仅限 ≤8 市场），不参与 ILS 搜索 |
| `io.py` + `cli.py` | 输入输出 | JSON 解析、参数解析、结果格式化 |

### Solution 的生命周期

- `Solution` 是 frozen dataclass，单个对象创建后不可变
- 算法中的"改进"是创建新 Solution 替换旧引用，不是原地修改
- ILS 同时持有 `current`（当前工作解）和 `incumbent`（历史最优）两个引用
- 最终 `incumbent` 被包进 `ILSResult` 作为输出

### 调用层次

```text
cli.py
  └── ils.py（总编排）
        ├── constructive.py
        ├── route_configuration.py ──→ neighborhoods.py（explore）
        ├── local_search.py ────────→ neighborhoods.py（explore）
        ├── perturbation.py（destroy/repair）
        └── diversity.py（diversity_constructive_heuristic）
```

所有算法模块最终汇聚到 `ils.py` 被编排；`domain/` 层的 model 和 evaluation 作为基础设施被所有模块引用。

## 源码分层与模块责任

```text
src/tpp/
├── domain/
│   ├── model.py                 # 不可变实例、解、ILS 参数与安全上限
│   └── evaluation.py            # 可行性、采购分配、方向旅行成本与总成本
├── core/
│   ├── local_solution/
│   │   ├── constructive.py      # Algorithm 2
│   │   ├── neighborhoods.py     # Algorithm 3：ADD/DROP/EXCHANGE/MOVE/SWITCH
│   │   ├── route_configuration.py # Algorithm 4
│   │   └── local_search.py      # Algorithm 5
│   └── ils_engine/
│       ├── perturbation.py       # Algorithms 6–7：Destroy/Repair
│       ├── diversity.py          # Algorithm 8 与共同出现记忆
│       └── ils.py                # Algorithm 9 主循环与 incumbent
├── exact.py                     # n <= 8 的独立穷举 oracle，不参与 ILS 搜索
├── io.py                        # JSON 输入和结果格式化
├── cli.py                       # 安全的命令行入口
└── __main__.py                  # python -m tpp 入口
```

修改时保持上述边界：

- 问题数据、通用成本和可行性规则放在 `domain/`，不复制到搜索算子中。
- 只构造或改进单个局部解的逻辑放在 `core/local_solution/`。
- 扰动、多样性记忆、重启和跨迭代状态放在 `core/ils_engine/`。
- `exact.py` 只作为独立正确性 oracle；不得让启发式求解器调用穷举结果来选择或修正解。
- CLI 和 I/O 层不实现算法逻辑；它们只负责参数、数据转换、错误边界和展示。

## 数据与解的不变量

- 仓库节点永远是 `0`；市场编号是 `1..n`。
- `travel_costs[i][j]` 表示从 `i` 到 `j` 的有向成本。读取、计算和测试时都不得假设 `c[i][j] == c[j][i]`。
- JSON 中 `travel_costs` 包含仓库行列；`market_purchase_costs` 刻意省略仓库行，并使用 `null` 表示某市场不售卖某商品。
- 合法路线必须以 `0` 开始和结束，中间只能出现有效市场，且同一市场不重复访问。
- 可行解必须覆盖所有商品。对每件商品，默认在已访问市场中选择最低价；价格并列时选市场编号较小者。
- 市场集合变化后，优先通过 `build_solution()` 完整重算采购分配和成本，不在多个算子中分散维护派生数据。
- `MOVE/SWITCH` 只能改变市场顺序，不能改变市场集合、商品分配或采购成本；`ADD/DROP/EXCHANGE` 可改变市场集合。
- 只有目标值严格降低超过 `EPSILON = 1e-9` 才算改进。总成本并列时使用路线 tuple 做确定性破平局。
- `TPPInstance`、`Solution`、`ILSConfig` 和 `ILSResult` 当前都是不可变 dataclass；不要引入隐式原地修改。

## 论文算法一致性

修改核心搜索时，必须对照 `docs/SECTION2_REPRODUCTION_PLAN.md` 中的论文—代码映射，特别守住以下约定：

- `Explore` 是遍历整个邻域的 best-improvement，不得静默替换为 first-improvement。
- `RouteConfiguration` 的顺序是有限 `ADD` → 有限 `DROP` → 有限 `EXCHANGE` → `DROP` 到局部最优。
- `LocalSearch` 从同一输入比较论文定义的三种 `MOVE/SWITCH` 搜索序列，不改变已访问市场集合。
- `Destroy` 删除 `ceil(alpha * m)` 个已访问市场，随机数必须来自 `ILSConfig.seed` 初始化的独立 `random.Random`。
- `Repair` 和 Diversity 构造使用路线节点对共同出现记忆；记忆包含仓库，并保持对称。
- ILS 扰动当前局部解 `x`，而不是每次回到 `incumbent`；只在严格改进时更新 `incumbent`。
- 论文未完全规定的并列规则已记录在复现计划第 6 节。如果修改这些规则，必须同步测试与文档，并说明这是复现约定变更。

## 开发与验证工作流

本项目要求 Python `>= 3.9`，当前运行时仅使用标准库。未经用户同意，不引入 NumPy、NetworkX、PyTorch 或其他第三方运行依赖。

从仓库根目录运行：

```bash
# 全部单元测试
PYTHONPATH=src python3 -m unittest discover -s tests -v

# 论文四市场实例 + 随机极小实例 + 穷举对照
PYTHONPATH=src python3 scripts/verify_small_instances.py

# 安全的 ILS-RC 命令行回归
PYTHONPATH=src python3 -m tpp.cli solve examples/paper_four_market.json \
  --k-max 20 --lambda-max 5 --alpha 0.5 --seed 0

# 独立穷举 oracle，仅限市场数 <= 8
PYTHONPATH=src python3 -m tpp.cli exact examples/paper_four_market.json
```

根据变更范围选择验证：

| 变更位置 | 最低验证要求 |
|---|---|
| `domain/model.py` 或 `domain/evaluation.py` | 全部单元测试 + `verify_small_instances.py` |
| `core/local_solution/` | 对应算子测试 + 全部单元测试 + 论文实例 |
| `core/ils_engine/` | 全部单元测试 + 固定种子重复运行 + `verify_small_instances.py` |
| `exact.py` | 穷举上限测试 + 论文实例精确结果 |
| `io.py` / `cli.py` / 示例 JSON | CLI 成功路径 + 非法输入失败路径 + 全部单元测试 |
| 文档或目录结构 | 检查所有路径和命令仍然有效 |

验证的固定正确性锚点是：

```text
route: 0 -> 3 -> 2 -> 0
item_markets: 3, 2, 3
travel_cost: 57
purchase_cost: 64
total_cost: 121
```

- 启发式解必须可行，且不得优于独立穷举 oracle 的真实最优值。
- 不要把某个随机实例未命中全局最优视为错误；应检查可行性、可复现性和 optimality gap。
- 修改随机搜索时必须显式固定并记录种子，不使用进程级全局随机状态。
- 验证输出只有在实际重新运行后才能写入 `docs/VERIFICATION.md`；运行时间不作为精确回归值。

## 代码与文档约定

- 优先使用类型标注、不可变数据和小而单一责任的函数，保持 Python 3.9 兼容。
- 新增或修改邻域算子时，每个算子至少要有可行性、不劣性/改进性和不变量测试。
- 论文对应关系、并列规则或默认参数发生变化时，同步更新 `README.md`、`docs/SECTION2_REPRODUCTION_PLAN.md` 和相关测试。
- 只有验证环境、命令或实际输出变化时，才更新 `docs/VERIFICATION.md`，并保留真实输出。
- 不把 `.DS_Store`、`__pycache__/`、虚拟环境、coverage 文件、build 产物或临时实验输出加入版本库。
- 完成代码变更后，交付说明至少包含：改了哪些文件、算法对应关系、运行的验证命令、真实验证结果、剩余差异或限制。

## 项目内 Archify Skill

项目的架构图、工作流程图、时序图、数据流图和生命周期图使用仓库内技能：

```text
skills/archify/SKILL.md
```

当用户要求可视化系统架构、技术工作流、API 调用顺序、数据管道、状态机，或转换与美化 Mermaid 时，执行前必须完整读取该 `SKILL.md`，并按其要求生成、验证和交付产物。

## 项目内 Emoji Commit Skill

项目提交代码时使用仓库内技能：

```text
skills/emoji-commit/SKILL.md
```

凡涉及提交、生成提交信息或拆分提交的请求，执行前必须完整读取该 `SKILL.md`，再根据本次请求读取它指定的 reference。不要仅凭本文件中的摘要替代技能原文。

### 触发条件

用户表达以下意图时，必须使用 `emoji-commit`：

- `commit`、`commit code`、`提交代码`、`帮我提交`、`自动提交`；
- `generate commit message`、`生成提交信息`、`write commit message`；
- `split commits`、`batch commit`、`分批提交`；
- 要求查看未提交变更并按逻辑分类提交。

普通代码编写、测试、解释或只查看 `git status` 不会自动触发提交。

### 提交前检查

1. 先运行 `git status --short`，查看完整工作区，不只查看 staged 文件。
2. 保留用户已有改动，不得为了提交而丢弃、覆盖或回滚无关文件。
3. 解析以下配置，并递归合并 local 配置：

   ```text
   .agents/fex-skills.config.json
   .agents/fex-skills.config.local.json
   ```

4. 同名配置以 `.local` 为准。
5. 提交语言优先级为：用户本轮明确指定 > local 配置 > 项目配置 > 默认 `en`。
6. `emoji-commit.language` 仅支持 `en` 和 `zh`。中文对话不代表提交信息必须使用中文。
7. 如果 `.agents/fex-skills.config.local.json` 存在但没有被 Git 忽略，必须停止提交，先提示加入 `.gitignore` 或移除该本地配置。
8. 最终说明中记录本次解析结果，例如 `emoji-commit.language=en`。

### Single Commit 路由

以下情况使用 single commit：

- 用户明确要求只提交暂存区；
- 工作区除 staged 变更外已经干净；
- 所有变更属于同一个不可再拆分的逻辑目的。

确定走 single commit 后，必须完整读取：

```text
skills/emoji-commit/references/single-commit.md
```

然后分析 staged diff、生成提交信息、执行提交并按 reference 完成自检。

### Batch Commit 路由

以下情况使用 batch commit：

- 用户明确要求 split commits、batch commit 或按逻辑分批提交；
- 工作区仍有 unstaged 或 untracked 变更；
- 业务代码、测试、文档或项目技能等变更具有多个独立目的。

确定走 batch commit 后，必须完整读取：

```text
skills/emoji-commit/references/batch-commit.md
```

Batch commit 必须遵守以下顺序：

```text
inventory -> plan -> preview -> 用户确认 -> apply -> 自检
```

- 在 preview 阶段只展示计划，不执行 commit。
- 未得到用户明确确认，不得 apply。
- 默认使用技能提供的执行器：

  ```text
  skills/emoji-commit/scripts/commit_batches.py
  ```

- preview 出现 `whitespace-only`、`suspicious-frontmatter`、`suspicious-lock-drift` 等风险时，必须先向用户说明。
- `skills/emoji-commit/` 自身发生变化时，默认与业务代码分开，作为独立的 skill package 提交。

### Commit Message 约束

提交信息必须遵守 `emoji-commit` 的 FEX Conventional Commits 规范。需要完整规范时读取：

```text
skills/emoji-commit/references/fex-conventional-commits.md
```

需要查询 emoji 类型时读取：

```text
skills/emoji-commit/references/cz-emoji-types.md
```

最低硬性要求：

- Header 只能使用下列骨架之一：

  ```text
  :emoji: subject
  :emoji: ! subject
  :emoji: (scope) subject
  :emoji: (scope) ! subject
  ```

- emoji 必须使用 `:sparkles:`、`:bug:` 等 shortcode，不能使用 Unicode emoji。
- `scope` 可选；存在时必须写为 `(scope)`。
- breaking marker `!` 必须独立放在 emoji 或 scope 之后、subject 之前。
- Header 与 Body 之间保留一个空行。
- Body 使用简洁的 bullet 风格。
- 若有 Footer，Body 与 Footer 之间保留一个空行。
- Jira 上下文统一写成单行 `Jira-Refs: KEY1, KEY2`，不保留原始 Jira URL。
- `BREAKING CHANGE:` 必须位于 `AI-Co-Authored-By:` 之前。
- 最终提交信息必须包含且仅包含一行 `AI-Co-Authored-By:`，并且它必须是最后一行。
- 禁止使用 `Co-authored-by` 或 `Co-Authored-By` 标准 trailer。

### 提交与推送边界

- 用户要求 commit 只授权本地提交，不自动授权 push。
- 只有用户明确要求 push、同步远程或同时说 commit and push 时才允许推送。
- 批量提交的用户确认只授权 apply commit；若 preview 中未明确包含 push，仍不得自动推送。
- 提交或推送完成后，报告提交哈希、标题、分支、远程同步状态和剩余工作区状态。

### 异常处理

遇到 hook 失败、配置错误、部分批次提交成功、工作区状态漂移或其他异常时，读取：

```text
skills/emoji-commit/references/troubleshooting.md
```

不得通过跳过 hook、强制覆盖用户变更或改写历史来绕过错误，除非用户明确授权相应操作。
