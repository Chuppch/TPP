# TPP ILS-RC 论文算法复现

本项目用于复现 Traveling Purchaser Problem（TPP，旅行采购商问题）的 ILS-RC 启发式算法。

目标论文：

> Tomás Kapancioglu and Raquel Bernardino.  
> *An iterated local search algorithm for the traveling purchaser problem*.  
> European Journal of Operational Research, 324 (2025), 759–772.

## 问题简介

TPP 是 Traveling Salesman Problem（TSP）的推广。采购者需要从仓库出发，访问部分市场购买清单中的全部商品，最后返回仓库。求解过程需要同时决定：

1. 访问哪些市场；
2. 按什么顺序访问；
3. 每件商品在哪个已访问市场购买。

优化目标是最小化总成本：

```text
总成本 = 旅行成本 + 采购成本
```

本项目面向 unrestricted TPP（UTPP），支持：

- 对称实例：`c[i][j] == c[j][i]`；
- 非对称实例：允许 `c[i][j] != c[j][i]`。

## ILS-RC 算法流程

论文算法由以下部分组成：

1. **Constructive Heuristic**：构造覆盖全部商品的可行初始解；
2. **Route Configuration**：通过 `ADD`、`DROP`、`EXCHANGE` 调整访问市场集合；
3. **Local Search**：通过 `MOVE`、`SWITCH` 优化已选市场的访问顺序；
4. **Destroy / Repair**：扰动当前局部最优解并恢复商品覆盖；
5. **Diversity Constructive Heuristic**：连续多次未改进时重新构造差异较大的解；
6. **ILS 主循环**：重复扰动与局部优化，保存迭代过程中发现的最佳解 `incumbent`。

需要注意：ILS-RC 是启发式算法，输出是搜索过程中发现的最好解，不保证一定是数学意义上的全局最优解。

## 开发与运行约束

- 运行平台：macOS；
- 计算设备：纯 CPU；
- 禁止使用 CUDA、GPU 和 Apple MPS；
- 常规开发与测试限制为 `n <= 50`；
- 穷举验证仅允许市场数 `n <= 8`；
- 默认单进程、低并发，不运行大规模参数扫描；
- 常规 ILS 测试的迭代上限不超过 1000。

## 项目目录

```text
TPP/
├── README.md
├── docs/         # Section 2 复现计划与验证记录
├── src/tpp/
│   ├── core/
│   │   ├── local_solution/ # 构造并改进局部最优解
│   │   └── ils_engine/     # 扰动、多样性与 ILS 循环
│   ├── domain/   # 数据模型、可行性和成本计算
│   └── *.py      # CLI、输入输出与穷举器
├── tests/        # 单元测试
├── examples/     # 论文示例和小规模输入
└── scripts/      # 极小实例穷举验证入口
```

## 快速运行

项目仅使用 Python 标准库，不需要安装第三方依赖。

运行论文四市场实例：

```bash
PYTHONPATH=src python3 -m tpp.cli solve examples/paper_four_market.json \
  --k-max 20 --lambda-max 5 --alpha 0.5 --seed 0
```

运行独立穷举求解器：

```bash
PYTHONPATH=src python3 -m tpp.cli exact examples/paper_four_market.json
```

运行全部单元测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

运行论文示例和随机极小实例验证：

```bash
PYTHONPATH=src python3 scripts/verify_small_instances.py
```

CLI 默认参数是面向本地小规模验证的安全参数，不代表论文 Section 3 中针对完整 benchmark 调优后的参数。

## 验证基准

第一项固定回归测试使用论文给出的四市场、三商品非对称实例。参考最优方案为：

```text
路线：0 -> 3 -> 2 -> 0
旅行成本：57
采购成本：64
总成本：121
```

其中商品 1 和商品 3 在市场 3 购买，商品 2 在市场 2 购买。

当前验证已使用 `n <= 8` 的极小随机实例进行穷举，将启发式解与真实最优值对照，以检查成本计算、商品覆盖和解的可行性。实际验证记录见 `docs/VERIFICATION.md`。

## 已完成基线

- [x] 初始化 Git 仓库与 README；
- [x] 实现问题数据结构和成本计算；
- [x] 实现初始解构造；
- [x] 实现 Route Configuration；
- [x] 实现 Local Search；
- [x] 实现 Destroy / Repair 与 ILS 主循环；
- [x] 实现穷举验证器；
- [x] 添加验证脚本和验证输出。

## 下一步 TODO

### 正确性与工程化

- [ ] 补充 CLI、JSON 读取和非法输入的单元测试；
- [ ] 将 20 组固定种子随机实例回归整合为可直接重复运行的验证入口；
- [ ] 增加对称、非对称及边界极小实例，持续与独立穷举 oracle 对照；
- [ ] 增加安装后命令行入口 `tpp-ils-rc` 的 smoke test。

### 论文一致性

- [ ] 继续核对并列选择、邻域遍历顺序和停止条件，并记录论文未完全规定的实现约定；
- [ ] 获取论文使用的 benchmark 实例与完整参数后，复现 Section 3 实验；
- [ ] 按论文的运行次数和统计方法，记录 optimality gap、运行时间和与已发表结果的差异。

### 后续优化

- [ ] 在不改变原始基线语义的前提下，对邻域枚举和成本重算进行纯 CPU 性能分析；
- [ ] 任何新算子或加速机制都作为可关闭扩展，与论文 ILS-RC 基线分开验证和报告。

## 复现边界

本项目首先追求算法流程、目标函数和算子行为与论文描述一致。由于作者原始代码、并列选择规则、邻域遍历顺序和完整随机状态可能未公开，因此不预先承诺逐项复现论文实验表格中的所有数值。

Chuppch
