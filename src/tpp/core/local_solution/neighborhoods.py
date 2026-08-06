"""Algorithm 3 and the five neighborhoods defined in Section 2.3."""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum

from ...domain.evaluation import (
    EPSILON,
    InfeasibleSolutionError,
    build_solution,
    is_strictly_better,
)
from ...domain.model import Solution, TPPInstance


class Neighborhood(str, Enum):
    ADD = "add"
    DROP = "drop"
    EXCHANGE = "exchange"
    MOVE = "move"
    SWITCH = "switch"


def _route_from_markets(markets: list[int]) -> tuple[int, ...]:
    return (0, *markets, 0)


def add_neighbors(instance: TPPInstance, solution: Solution) -> Iterator[Solution]:
    markets = list(solution.visited_markets)
    unvisited = sorted(set(instance.markets) - set(markets))
    for market in unvisited:
        for position in range(len(markets) + 1):
            candidate_markets = markets.copy()
            candidate_markets.insert(position, market)
            yield build_solution(instance, _route_from_markets(candidate_markets))


def drop_neighbors(instance: TPPInstance, solution: Solution) -> Iterator[Solution]:
    markets = list(solution.visited_markets)
    for position in range(len(markets)):
        candidate_markets = markets.copy()
        candidate_markets.pop(position)
        try:
            yield build_solution(instance, _route_from_markets(candidate_markets))
        except InfeasibleSolutionError:
            continue


def exchange_neighbors(instance: TPPInstance, solution: Solution) -> Iterator[Solution]:
    markets = list(solution.visited_markets)
    unvisited = sorted(set(instance.markets) - set(markets))
    for position in range(len(markets)):
        for market in unvisited:
            candidate_markets = markets.copy()
            candidate_markets[position] = market
            try:
                yield build_solution(instance, _route_from_markets(candidate_markets))
            except InfeasibleSolutionError:
                continue


def move_neighbors(instance: TPPInstance, solution: Solution) -> Iterator[Solution]:
    markets = list(solution.visited_markets)
    for old_position in range(len(markets)):
        for new_position in range(len(markets)):
            if old_position == new_position:
                continue
            candidate_markets = markets.copy()
            market = candidate_markets.pop(old_position)
            candidate_markets.insert(new_position, market)
            yield build_solution(instance, _route_from_markets(candidate_markets))


def switch_neighbors(instance: TPPInstance, solution: Solution) -> Iterator[Solution]:
    markets = list(solution.visited_markets)
    for left in range(len(markets)):
        for right in range(left + 1, len(markets)):
            candidate_markets = markets.copy()
            candidate_markets[left], candidate_markets[right] = (
                candidate_markets[right],
                candidate_markets[left],
            )
            yield build_solution(instance, _route_from_markets(candidate_markets))


def iter_neighbors(
    instance: TPPInstance, solution: Solution, neighborhood: Neighborhood
) -> Iterator[Solution]:
    if neighborhood is Neighborhood.ADD:
        return add_neighbors(instance, solution)
    if neighborhood is Neighborhood.DROP:
        return drop_neighbors(instance, solution)
    if neighborhood is Neighborhood.EXCHANGE:
        return exchange_neighbors(instance, solution)
    if neighborhood is Neighborhood.MOVE:
        return move_neighbors(instance, solution)
    if neighborhood is Neighborhood.SWITCH:
        return switch_neighbors(instance, solution)
    raise ValueError(f"Unsupported neighborhood: {neighborhood}")


def best_neighbor(
    instance: TPPInstance, solution: Solution, neighborhood: Neighborhood
) -> Solution:
    """Return the best-improvement neighbor, including the original solution."""

    best = solution
    for candidate in iter_neighbors(instance, solution, neighborhood):
        if is_strictly_better(candidate, best):
            best = candidate
        elif (
            abs(candidate.total_cost - best.total_cost) <= EPSILON
            and is_strictly_better(candidate, solution)
            and candidate.route < best.route
        ):
            best = candidate
    return best


def explore(
    instance: TPPInstance,
    solution: Solution,
    neighborhood: Neighborhood,
    delta: int | None,
) -> Solution:
    """Algorithm 3.

    ``delta=None`` represents the paper's ``+infinity`` and therefore
    searches until a local optimum is reached.
    """

    if delta is not None and delta < 0:
        raise ValueError("delta must be non-negative or None.")
    current = solution
    searches = 0
    while delta is None or searches < delta:
        candidate = best_neighbor(instance, current, neighborhood)
        searches += 1
        if not is_strictly_better(candidate, current):
            break
        current = candidate
    return current
