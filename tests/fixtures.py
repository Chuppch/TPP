from __future__ import annotations

import random

from tpp.domain.model import TPPInstance


def paper_instance() -> TPPInstance:
    return TPPInstance.from_market_matrices(
        "paper-four-market-asymmetric",
        [
            [0, 15, 30, 18, 16],
            [30, 0, 19, 24, 27],
            [24, 30, 0, 27, 20],
            [24, 18, 15, 0, 24],
            [19, 15, 23, 26, 0],
        ],
        [
            [None, None, 24],
            [None, 21, 26],
            [23, None, 20],
            [29, 30, 28],
        ],
    )


def random_instance(seed: int, market_count: int = 5, item_count: int = 4) -> TPPInstance:
    rng = random.Random(seed)
    node_count = market_count + 1
    travel = [[0.0 for _ in range(node_count)] for _ in range(node_count)]
    for start in range(node_count):
        for end in range(node_count):
            if start != end:
                travel[start][end] = float(rng.randint(5, 40))

    prices: list[list[float | None]] = []
    for _market in range(market_count):
        prices.append(
            [float(rng.randint(10, 60)) if rng.random() < 0.6 else None for _ in range(item_count)]
        )
    for item in range(item_count):
        if not any(row[item] is not None for row in prices):
            prices[rng.randrange(market_count)][item] = float(rng.randint(10, 60))
    return TPPInstance.from_market_matrices(f"random-{seed}", travel, prices)
