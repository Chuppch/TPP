"""Algorithm 2: constructive heuristic from Section 2.2."""

from __future__ import annotations

from ...domain.evaluation import build_solution
from ...domain.model import Solution, TPPInstance


def constructive_heuristic(instance: TPPInstance) -> Solution:
    """Create a feasible solution exactly in the two phases of Algorithm 2."""

    candidates = set(instance.markets)
    selected: set[int] = set()
    missing = set(instance.items)

    while missing:
        scored: list[tuple[int, float, int]] = []
        for market in sorted(candidates):
            available = [item for item in missing if instance.sells(market, item)]
            if not available:
                continue
            average_price = sum(
                float(instance.purchase_costs[market][item]) for item in available
            ) / len(available)
            scored.append((-len(available), average_price, market))
        if not scored:
            raise ValueError("No remaining market can cover the missing items.")

        _, _, chosen = min(scored)
        selected.add(chosen)
        candidates.remove(chosen)
        missing = {item for item in missing if not instance.sells(chosen, item)}

    route = [0]
    current = 0
    remaining = set(selected)
    while remaining:
        chosen = min(
            remaining,
            key=lambda market: (instance.travel_costs[current][market], market),
        )
        route.append(chosen)
        remaining.remove(chosen)
        current = chosen
    route.append(0)
    return build_solution(instance, route)
