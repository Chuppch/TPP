# TPP 相关求解方法与论文索引

## 文档目的

本文档整理 Traveling Purchaser Problem（TPP）的几类代表性求解方法，用于：

- 理解不同方法如何解决同一个 TPP 问题；
- 区分经典 UTPP 与 TPP 扩展变体；
- 为当前 ILS-RC 复现项目的后续优化提供参考；
- 记录论文、代码和数据的公开情况。

> 注意：下列工作都与 TPP 求解有关，但并不都是在 Kapancioglu 与 Bernardino（2025）的 ILS-RC 源码上直接修改。更准确地说，它们是解决 TPP 或其扩展变体的不同算法路线。

## 方法总览

| 方法 | 论文 | 解决对象 | 公开代码情况 |
| --- | --- | --- | --- |
| ILS-RC | [An iterated local search algorithm for the traveling purchaser problem](https://doi.org/10.1016/j.ejor.2025.02.024) | 经典 UTPP，也是当前项目复现的论文 | 未见作者官方代码 |
| 深度强化学习 | [Deep Reinforcement Learning for Traveling Purchaser Problems](https://arxiv.org/abs/2404.02476)；[IEEE 版本](https://doi.org/10.1109/TETCI.2025.3581113) | 经典 TPP；策略网络构造路线，再通过线性规划确定采购方案 | [官方代码 DRL4TPP](https://github.com/Xyz-yuanhf/drl4tpp) |
| ALNS | [The traveling purchaser problem with fast service option](https://doi.org/10.1016/j.cor.2022.105700) | TPP-FSO 扩展变体；增加路线时限和快速服务选项，核心算法为自适应 Destroy/Repair | 未找到官方完整代码 |
| Matheuristic / M-ALNS | [The traveling purchaser problem with promotional packages](https://doi.org/10.1111/itor.70106)；[开放 PDF](https://acikerisim.uludag.edu.tr/bitstreams/d220d5d7-10a0-46e0-84bb-55d2f49cf782/download) | TPP-PP 扩展变体；增加促销套餐，将 ALNS 与精确求解器结合 | 提供问题数据集，但未见完整官方求解代码 |
| 自动进化算子 | [LLM-Driven Co-Evolutionary Automated Heuristic Design for Bi-Component Coupled Combinatorial Optimization](https://arxiv.org/abs/2606.00718) | 同时优化 TPP 的市场—路线算子和购买算子，并引用 ILS-RC | 新预印本，整理时未找到官方完整代码 |
| GRASP + Path Relinking | [A GRASP/Path-Relinking algorithm for the traveling purchaser problem](https://doi.org/10.1111/itor.12985) | 经典对称与非对称 TPP；使用多种构造策略、精英解重组和过滤策略 | 未见作者官方代码 |

## 方法与当前项目的关系

### 1. ILS-RC：当前复现基线

ILS-RC 使用人工设计的构造、邻域搜索、扰动和多样性重启机制。当前项目对应的主要流程是：

```text
Constructive Heuristic
  -> Route Configuration (ADD / DROP / EXCHANGE)
  -> Local Search (MOVE / SWITCH)
  -> Destroy / Repair
  -> Diversity Restart
  -> 保存 incumbent
```

它是后续实验的基线。任何新机制都应作为可关闭扩展，并与该基线分开验证。

### 2. 深度强化学习：学习路线构造策略

该方法使用市场—商品二部图表示 TPP，由策略网络逐步构造路线。路线确定后，再用线性规划求采购方案。

它与 ILS-RC 是并列的求解路线，不是在 ILS-RC 代码中简单加入一层神经网络。官方仓库提供了训练、评估、预训练模型和 TPPLIB 评测入口，是本索引中代码资料最完整的方法。

### 3. ALNS：自适应选择大扰动算子

ALNS 准备多组 Destroy 和 Repair 算子，根据近期搜索效果动态调整它们的选择权重。论文研究的是带时间限制和快速服务的 TPP-FSO，不是当前项目的经典 UTPP，但自适应算子选择机制可以作为 ILS-RC 的扩展参考。

### 4. Matheuristic / M-ALNS：启发式与精确求解结合

该方法使用 ALNS 探索市场和路线结构，再对有潜力的解调用精确求解器，继续优化采购方案。论文具体解决 TPP-PP 促销套餐变体，其可借鉴的核心是“启发式负责广度探索，数学规划负责局部精确优化”。

### 5. 自动进化算子：联合设计路线与购买规则

CoEvo-AHD 将 TPP 视为两个相互耦合的决策部分：

- 市场选择与路线调整；
- 商品采购方案调整。

它维护两组算子种群，使用 LLM 生成和改写算子，并通过完整解的效果评价算子组合。它明确引用了 ILS-RC，但提出的是新的自动启发式设计框架，而非对 ILS-RC 源码的简单增量修改。

### 6. GRASP + Path Relinking：精英解重组与过滤

该方法使用三种构造过程：`route-first`、`purchase-first` 和 `purchase-and-route`，并使用 `insert` 与 `remove` 局部搜索算子。Path Relinking 通过重组精英解进行强化搜索，Filtering 则避免在低潜力解上执行昂贵的局部搜索。

该思路可用于扩展当前项目的 `incumbent` 机制：从只保存一个历史最优解，扩展为保存一组具有质量和多样性的精英解。

## 关系总结

```text
                          TPP 问题
                              |
        +---------------------+----------------------+
        |                     |                      |
     ILS-RC                 ALNS                 深度强化学习
  局部搜索+扰动        自适应大邻域          学习路线构造策略
        |                     |                      |
        |                 Matheuristic               |
        |             启发式+精确求解              |
        +---------------------+----------------------+
                              |
                可进一步加入精英解重组
                    或自动进化算子
```

因此，这些方法的关系主要是：

- 它们都用于搜索低成本的 TPP 解；
- 它们在搜索框架、路线构造方式和采购优化方式上不同；
- 部分论文解决经典 TPP，部分论文解决带时限、快速服务或促销套餐的扩展变体；
- 不能将它们统称为“基于 ILS-RC 源码的优化”；
- 它们可以作为当前 ILS-RC 基线的后续混合与对比方法。

## 建议阅读顺序

1. **ILS-RC**：理解当前项目的基线和五类邻域算子。
2. **ALNS TPP-FSO**：理解多组 Destroy/Repair 和动态算子权重。
3. **GRASP + Path Relinking**：理解精英解池、解重组和搜索过滤。
4. **DRL4TPP**：理解如何将路线构造与采购计划拆分，以及神经网络在 TPP 中的角色。
5. **M-ALNS**：理解启发式搜索与精确求解器的混合。
6. **CoEvo-AHD**：了解自动设计和协同进化 TPP 算子的前沿方向。

## 面向当前项目的参考优先级

在 macOS、纯 CPU 和小规模验证的约束下，对当前 ILS-RC 项目的参考优先级为：

1. 借鉴 ALNS，实现多组可关闭的 Destroy/Repair 算子和自适应选择机制；
2. 借鉴 GRASP + Path Relinking，实现小型精英解池与解重组；
3. 借鉴 Matheuristic，对路线确定后的采购方案进行独立精确优化；
4. 将深度强化学习和 LLM 自动算子设计作为更高成本的后续方向，不纳入当前纯 CPU 基线。

后续如实现任何扩展，应保留原始 ILS-RC 开关和基线行为，并分别记录解质量、运行时间、随机种子和消融结果。
