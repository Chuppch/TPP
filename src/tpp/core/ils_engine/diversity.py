"""Diversity memory and Algorithm 8 from Section 2.7."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from ...domain.evaluation import build_solution, missing_items, travel_cost
from ...domain.model import Solution, TPPInstance


@dataclass
class DiversityMemory:
    """Symmetric co-occurrence counts Delta_ij used by Algorithms 7 and 8."""

    counts: list[list[int]]

    @classmethod
    def empty(cls, node_count: int) -> "DiversityMemory":
        return cls([[0 for _ in range(node_count)] for _ in range(node_count)])

    def score(self, market: int, route: tuple[int, ...] | list[int]) -> int:
        return sum(self.counts[market][node] for node in set(route))

    def record(self, route: tuple[int, ...] | list[int]) -> None:
        for left, right in combinations(sorted(set(route)), 2):
            self.counts[left][right] += 1
            self.counts[right][left] += 1


def _best_insertion_route(
    instance: TPPInstance, route: tuple[int, ...] | list[int], market: int
) -> tuple[int, ...]:
    base = list(route)
    candidates: list[tuple[float, int, tuple[int, ...]]] = []
    for position in range(1, len(base)):
        candidate = base.copy()
        candidate.insert(position, market)
        normalized = tuple(candidate)
        candidates.append((travel_cost(instance, normalized), position, normalized))
    return min(candidates, key=lambda value: (value[0], value[1]))[2]


def diversity_constructive_heuristic(
    instance: TPPInstance, memory: DiversityMemory
) -> Solution:
    """Algorithm 8. Recording the resulting route is the caller's duty."""

    route: tuple[int, ...] = (0, 0)
    candidates = set(instance.markets)

    while True:
        missing = missing_items(instance, route)
        if not missing:
            break
        if not candidates:
            raise ValueError("Diversity construction exhausted all markets before feasibility.")

        scores = {market: memory.score(market, route) for market in candidates}
        minimum_score = min(scores.values())
        lowest = {market for market, score in scores.items() if score == minimum_score}
        useful = [
            market
            for market in lowest
            if any(instance.sells(market, item) for item in missing)
        ]
        if not useful:
            candidates.difference_update(lowest)
            continue

        chosen = min(
            useful,
            key=lambda market: (
                -sum(instance.sells(market, item) for item in missing),
                market,
            ),
        )
        route = _best_insertion_route(instance, route, chosen)
        candidates.remove(chosen)

    return build_solution(instance, route)
