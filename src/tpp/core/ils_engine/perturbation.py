"""Algorithms 6 and 7: destroy and repair perturbation."""

from __future__ import annotations

import math
import random

from .diversity import DiversityMemory, _best_insertion_route
from ...domain.evaluation import build_solution, missing_items
from ...domain.model import Solution, TPPInstance


def destroy(solution: Solution, alpha: float, rng: random.Random) -> tuple[int, ...]:
    """Algorithm 6: uniformly remove ceil(alpha * m) visited markets."""

    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in the interval (0, 1].")
    markets = list(solution.visited_markets)
    if not markets:
        raise ValueError("A feasible TPP route must contain at least one market.")
    remove_count = min(len(markets), max(1, math.ceil(alpha * len(markets))))
    removed = set(rng.sample(markets, remove_count))
    return (0, *(market for market in markets if market not in removed), 0)


def repair(
    instance: TPPInstance,
    destroyed_route: tuple[int, ...] | list[int],
    memory: DiversityMemory,
) -> Solution:
    """Algorithm 7: restore item coverage using the diversity metric G_iR."""

    route = tuple(destroyed_route)
    candidates = set(instance.markets) - set(route[1:-1])

    while True:
        missing = missing_items(instance, route)
        if not missing:
            return build_solution(instance, route)
        if not candidates:
            raise ValueError("Repair exhausted all markets before restoring feasibility.")

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
