# ILS-RC 复现验证记录

## 验证环境

```text
日期：2026-08-07
系统：macOS / Darwin arm64
Python：3.9.6
计算设备：纯 CPU
并发：单进程
GPU / CUDA / MPS：未使用
```

## 验证命令

### 单元测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

### 论文示例与极小实例穷举对照

```bash
PYTHONPATH=src python3 scripts/verify_small_instances.py
```

### 额外随机回归

使用 20 个固定种子的五市场、四商品实例，对称和非对称旅行成本交替生成。每个实例都通过独立穷举器计算真实最优值，再检查 ILS-RC 解的可行性与目标值下界关系。

## 实际输出

### 单元测试摘要

```text
Ran 20 tests in 0.037s

OK
```

覆盖内容包括：

- 非对称旅行成本方向；
- 商品覆盖与采购分配；
- Constructive Heuristic；
- ADD、DROP、EXCHANGE、MOVE、SWITCH；
- best-improvement Explore；
- Route Configuration；
- Local Search；
- Destroy、Repair 和 Diversity Memory；
- ILS-RC 固定随机种子复现；
- 八市场穷举保护上限。

### 论文示例与三个随机极小实例

```text
CPU-only verification: one process, markets <= 5, exact limit <= 8
paper-four-market: exact=121, ils=121, gap=0.000%, elapsed=0.006429s
tiny-symmetric-7: exact=141, ils=141, gap=0.000%, elapsed=0.014797s
tiny-asymmetric-13: exact=134, ils=134, gap=0.000%, elapsed=0.018987s
tiny-symmetric-29: exact=222, ils=222, gap=0.000%, elapsed=0.022749s
verification_status: PASS
```

运行时间会受机器状态影响，正确性判断不依赖具体耗时。

### 20 个随机实例回归

```text
random_instances_checked=20 worst_gap=1.639% status=PASS
```

该结果表示全部启发式解均可行，且没有出现低于独立穷举最优值的错误。最差 gap 为 1.639%，符合启发式算法不保证每次命中全局最优的预期。

## 论文四市场固定回归结果

```text
route: 0 -> 3 -> 2 -> 0
purchases: item 1->market 3, item 2->market 2, item 3->market 3
travel_cost: 57
purchase_cost: 64
total_cost: 121
```

反向路线 `0 -> 2 -> 3 -> 0` 的旅行成本为 81、总成本为 145，证明实现没有把非对称旅行成本矩阵错误地对称化。

## 验证结论

- Algorithms 2-9 均已有代码对应；
- 论文四市场实例与独立穷举结果一致；
- 对称与非对称极小实例验证通过；
- 固定随机种子时解和迭代统计可复现；
- 所有验证均在纯 CPU、小规模和单进程条件下完成。
