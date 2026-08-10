# 测试目录说明

```text
tests/
├── fixtures.py       # 共享的论文示例和随机极小实例构造器
├── unit/             # 单个组件的行为和不变量
└── integration/      # 跨组件执行链路
```

`unit/` 覆盖领域模型、成本计算、邻域算子、Route Configuration、Local Search、扰动、Diversity 和穷举 oracle。

`integration/` 覆盖完整 ILS 求解、JSON/CLI 边界和实验流水线。这些测试不参与正式求解，仅在开发验证时执行。

全部测试的命令保持不变：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

也可以分类运行：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/unit -v
PYTHONPATH=src python3 -m unittest discover -s tests/integration -v
```
