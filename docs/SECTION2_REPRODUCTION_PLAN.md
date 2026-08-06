# TPP ILS-RC Section 2 复现计划

## 1. 文档目的

本文档定义本仓库复现论文 Section 2 的工作范围、实现顺序、模块边界和验收标准。

目标论文：

> Tomás Kapancioglu and Raquel Bernardino.  
> *An iterated local search algorithm for the traveling purchaser problem*.  
> European Journal of Operational Research, 324 (2025), 759-772.  
> DOI: 10.1016/j.ejor.2025.02.024

第一阶段只复现论文原始 ILS-RC，不加入神经网络、禁忌搜索或论文之外的搜索算子。性能优化必须建立在原始基线通过验证之后，并与基线分开标注。

## 2. 复现目标

实现一个可在 macOS 纯 CPU 上运行的 unrestricted TPP（UTPP）求解器，支持：

- 完全有向图；
- 对称旅行成本；
- 非对称旅行成本；
- 单车辆、单仓库；
- 单件商品可由任意一个出售该商品的已访问市场满足；
- 目标函数为旅行成本与采购成本之和。

求解器需要输出：

- 完整路线；
- 已访问市场集合；
- 每件商品的购买市场；
- 旅行成本；
- 采购成本；
- 总成本；
- 随机种子和运行时间。

## 3. Section 2 与代码模块对应关系

| 论文内容 | 算法 | 计划模块 | 实现职责 |
|---|---:|---|---|
| 2.1 General framework | Algorithm 1 | `src/tpp/core/ils_engine/ils.py` | ILS 通用框架和 incumbent 管理 |
| 2.2 Constructive heuristic | Algorithm 2 | `src/tpp/core/local_solution/constructive.py` | 选择覆盖商品的市场并生成最近邻路线 |
| 2.3 Neighborhoods | Algorithm 3 | `src/tpp/core/local_solution/neighborhoods.py` | 五类邻域和 best-improvement Explore |
| 2.4 Route configuration | Algorithm 4 | `src/tpp/core/local_solution/route_configuration.py` | 按规定顺序调整市场集合 |
| 2.5 Local search | Algorithm 5 | `src/tpp/core/local_solution/local_search.py` | 三种 MOVE/SWITCH 搜索序列 |
| 2.6.1 Destroy operator | Algorithm 6 | `src/tpp/core/ils_engine/perturbation.py` | 随机删除指定比例的市场 |
| 2.6.2 Repair operator | Algorithm 7 | `src/tpp/core/ils_engine/perturbation.py` | 使用多样性指标恢复商品覆盖 |
| 2.7 Diversity control | Algorithm 8 | `src/tpp/core/ils_engine/diversity.py` | 基于历史共同出现次数重新构造解 |
| 2.8 ILS with route configuration | Algorithm 9 | `src/tpp/core/ils_engine/ils.py` | 完整 ILS-RC 主循环 |

基础数据和验证模块：

```text
src/tpp/domain/model.py       # TPPInstance、Solution 和参数对象
src/tpp/domain/evaluation.py  # 可行性、采购分配和成本计算
src/tpp/io.py                 # 极小实例数据读取与写出
src/tpp/exact.py              # n <= 8 的独立穷举验证器
src/tpp/cli.py                # 纯 CPU 命令行入口
```

## 4. 数据模型与目标函数

### 4.1 TPPInstance

保存以下不可变输入：

- 仓库编号固定为 `0`；
- 市场集合 `M \ {0}`；
- 商品集合 `K`；
- 有向旅行成本 `c[i][j]`；
- 商品价格 `p[k][i]`，不可购买使用空值表示；
- 每件商品对应的可购买市场集合 `M(k)`。

输入校验包括：

- 成本矩阵维度一致；
- 对角线不参与路线成本；
- 旅行成本非负；
- 每件商品至少在一个市场可购买；
- 非对称数据不得被自动对称化。

### 4.2 Solution

保存以下派生状态：

- 路线，包含首尾仓库，例如 `[0, 3, 2, 0]`；
- 已访问市场集合；
- `item -> market` 采购分配；
- 旅行成本；
- 采购成本；
- 总成本。

每次访问市场集合变化后，所有商品都重新分配到已访问市场中售价最低的位置。仅改变路线顺序时，采购分配和采购成本保持不变。

目标函数统一为：

```text
Z(x) = directional_travel_cost(x) + minimum_purchase_cost(x)
```

## 5. 分阶段实现任务

### 阶段 A：基础模型与可信成本计算

1. 创建项目包、测试目录和命令行入口。
2. 实现 `TPPInstance` 与 `Solution`。
3. 实现完整成本重算，不使用增量成本缓存。
4. 实现商品覆盖、路线结构和采购分配校验。
5. 添加非对称方向测试，确保 `c[i][j]` 与 `c[j][i]` 独立读取。

验收条件：给定任意手工路线，可以正确拆分旅行成本、采购成本和总成本，并识别不可行解。

### 阶段 B：Algorithm 2 - ConstructiveHeuristic

严格实现以下逻辑：

1. 未覆盖商品集合初始化为全部商品。
2. 对每个候选市场计算可覆盖的缺失商品数 `w_i`。
3. 优先选择 `w_i` 最大的市场。
4. 在上述市场中选择缺失商品平均采购价 `a_i` 最低者。
5. 重复选择市场，直到所有商品被覆盖。
6. 从仓库开始，以有向旅行成本执行最近邻排序。
7. 路线末尾加入仓库。
8. 在已访问市场中为每件商品选择最低购买价格。

验收条件：返回解始终可行，且同一输入和同一并列规则得到确定结果。

### 阶段 C：Algorithm 3 - Explore 与五类邻域

实现以下邻域：

- `N_add(x)`：把一个未访问市场插入路线的任意位置；
- `N_drop(x)`：移除一个已访问市场，候选解必须保持可行；
- `N_exchange(x)`：用一个未访问市场替换一个已访问市场；
- `N_move(x)`：将一个已访问市场移动到另一个路线位置；
- `N_switch(x)`：交换两个已访问市场的位置。

所有邻域都包含原解。每次邻域搜索必须检查全部候选，选择目标值最低的解，即论文规定的 best-improvement；不能替换为 first-improvement。

`Explore(x, N, delta)` 最多连续执行 `delta` 次 best-improvement；如果本轮最优候选就是原解，则立即停止。`delta = infinity` 表示搜索到该邻域局部最优。

验收条件：每个算子都有独立单元测试；所有返回解满足路线和商品覆盖约束。

### 阶段 D：Algorithm 4 - RouteConfiguration

严格保持论文顺序：

```text
Explore(ADD, delta_add)
Explore(DROP, delta_drop)
Explore(EXCHANGE, delta_exchange)
Explore(DROP, infinity)
```

最后一次 DROP 必须搜索到局部最优，用于移除不必要市场并稳定路线规模。

验收条件：输出不劣于输入，且最终不存在能够进一步改进目标值的可行 DROP。

### 阶段 E：Algorithm 5 - LocalSearch

从同一个输入解复制出 `x1`、`x2`、`x3`：

1. `x1`：MOVE 到局部最优，然后 SWITCH 到局部最优；
2. `x2`：SWITCH 到局部最优，然后 MOVE 到局部最优；
3. `x3`：单次 SWITCH、单次 MOVE交替执行，直到两者都不能改进；
4. 返回 `x1`、`x2`、`x3` 中目标值最低的解。

LocalSearch 不得改变访问市场集合，只能改变访问顺序。

验收条件：输出路线成本不高于输入；访问市场集合和采购成本保持不变。

### 阶段 F：Algorithms 6-7 - Destroy 与 Repair

Destroy：

- 计算 `ceil(alpha * m)`；
- 从当前路线的市场中均匀、无放回随机删除对应数量；
- 至少删除一个市场；
- 允许中间解暂时不满足商品覆盖。

Repair：

- 从未访问市场中选择能够出售至少一种缺失商品的市场；
- 优先最小化该市场与当前路线节点的共同出现次数之和 `G_iR`；
- 并列时选择能覆盖最多缺失商品的市场；
- 插入到使路线成本增加最少的位置；
- 重复执行，直到所有商品重新被覆盖；
- 最后重新确定所有商品的最低价购买市场。

共同出现统计必须包含仓库，以支持 Destroy 删除全部市场后的空路线情况。

验收条件：Destroy 的删除数量正确且可通过随机种子复现；Repair 总能在合法实例上恢复可行性。

### 阶段 G：Algorithm 8 - DiversityConstructiveHeuristic

1. 从仅包含首尾仓库的空路线开始。
2. 候选市场按 `G_ix` 最小值筛选。
3. 如果最小值候选均不能覆盖缺失商品，则从候选集移除后继续。
4. 否则选择其中覆盖缺失商品最多的市场。
5. 将市场插入旅行成本增加最小的位置。
6. 覆盖全部商品后重新确定采购分配。
7. 构造或扰动完成后，更新路线中节点对的共同出现次数 `Delta_ij`。

验收条件：重启结果可行，并且共同出现矩阵满足对称性 `Delta_ij = Delta_ji`。

### 阶段 H：Algorithm 9 - ILS-RC

完整主流程：

1. ConstructiveHeuristic；
2. RouteConfiguration；
3. LocalSearch；
4. 初始化 `incumbent`、`z` 和 `lambda = 0`；
5. 循环 `k = 1..k_max`；
6. 当 `lambda == lambda_max` 时执行 DiversityConstructiveHeuristic 并清零 `lambda`；
7. 否则对当前解执行 Destroy 后 Repair；
8. 对新解再次执行 RouteConfiguration 和 LocalSearch；
9. 严格改进 `z` 时更新 incumbent 并清零 `lambda`；
10. 未改进时 `lambda += 1`；
11. 返回 incumbent。

扰动作用于最近一次访问的局部最优解 `x`，而不是每次都回到 incumbent，保持论文所述 random-walk acceptance 行为。

验收条件：固定随机种子时输出完全可复现；迭代次数和 `lambda` 更新与 Algorithm 9 一致。

## 6. 论文未完全规定的实现约定

以下内容不得静默决定，需要在代码注释和最终说明中记录：

- 多个市场同时满足 Algorithm 2 的 `w_i` 和 `a_i` 条件时，默认取市场编号最小者；
- Repair 中 `G_iR` 和缺失商品覆盖数仍完全并列时，默认取市场编号最小者；
- 多个插入位置成本相同时，默认取路线中最靠前的位置；
- 多个邻域解总成本相同时保留当前解，只有严格降低目标值才算改进；
- 浮点比较使用统一容差；
- Destroy 使用固定种子的独立随机数生成器。

如果后续发现论文补充材料给出了不同规则，应以论文材料为准并更新此处。

## 7. 验证方案

### 7.1 论文四市场实例

固定回归结果：

```text
路线：0 -> 3 -> 2 -> 0
商品 1：市场 3，成本 23
商品 2：市场 2，成本 21
商品 3：市场 3，成本 20
旅行成本：18 + 15 + 24 = 57
采购成本：23 + 21 + 20 = 64
总成本：121
```

需要同时验证反向路线成本不同，证明非对称矩阵没有被误处理。

### 7.2 极小实例穷举

- 仅允许市场数 `n <= 8`；
- 穷举所有非空市场子集和访问排列；
- 对每条路线计算最低采购成本；
- 得到独立的真实最优值；
- 用于检查启发式成本计算、可行性和结果质量。

穷举器是测试 oracle，不参与 ILS-RC 的实际搜索。

### 7.3 随机回归测试

- 生成对称和非对称极小实例；
- 固定随机种子；
- 检查每个算子前后的不变量；
- 记录启发式解与真实最优值的 gap；
- 不要求启发式在所有随机实例上命中全局最优。

## 8. 计算资源保护

- 全程使用 CPU，禁止 CUDA、MPS 和其他 GPU 后端；
- 常规实例总节点数 `n <= 50`；
- 穷举实例市场数 `n <= 8`；
- 默认单进程，不启用多进程参数扫描；
- 常规 `k_max <= 1000`；
- CLI 必须检查规模和参数上限；
- 超过安全限制时直接报错，不自动继续运行。

## 9. 计划仓库结构

```text
TPP/
├── README.md
├── docs/
│   └── SECTION2_REPRODUCTION_PLAN.md
├── src/
│   └── tpp/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── local_solution/
│       │   │   ├── __init__.py
│       │   │   ├── constructive.py
│       │   │   ├── neighborhoods.py
│       │   │   ├── route_configuration.py
│       │   │   └── local_search.py
│       │   └── ils_engine/
│       │       ├── __init__.py
│       │       ├── perturbation.py
│       │       ├── diversity.py
│       │       └── ils.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── model.py
│       │   └── evaluation.py
│       ├── exact.py
│       ├── io.py
│       └── cli.py
├── examples/
│   └── paper_four_market.json
├── tests/
│   ├── fixtures.py
│   ├── test_model_and_evaluation.py
│   ├── test_constructive_and_neighborhoods.py
│   ├── test_route_and_local_search.py
│   ├── test_perturbation_and_diversity.py
│   └── test_ils_and_exact.py
└── scripts/
    └── verify_small_instances.py
```

## 10. 最终交付物

1. Section 2 对应的完整实现代码；
2. 论文四市场示例数据；
3. 极小实例穷举验证器；
4. 单元测试和一键验证脚本；
5. 固定随机种子的真实验证输出；
6. 实现与论文伪代码映射说明；
7. 论文未规定细节、实现约定和已知差异说明；
8. 所有修改文件清单和运行命令。

## 11. 完成标准

只有同时满足以下条件才视为复现完成：

- Algorithms 2-9 均有代码对应；
- Algorithm 3 使用 best-improvement；
- Route Configuration 和 LocalSearch 的调用顺序与论文一致；
- Destroy、Repair 和多样性统计行为可复现；
- 论文四市场实例得到总成本 121；
- 极小实例通过穷举一致性检查；
- 所有测试在 macOS 纯 CPU、小规模限制内通过；
- README、验证脚本和验证输出完整；
- 未将启发式最好解错误描述为保证的全局最优解。
