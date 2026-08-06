"""Feasibility and full objective evaluation for TPP routes."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from .model import Solution, TPPInstance


EPSILON = 1e-9


class InfeasibleSolutionError(ValueError):
    """Raised when a route cannot form a feasible TPP solution."""


def validate_route(instance: TPPInstance, route: Sequence[int]) -> tuple[int, ...]:
    normalized = tuple(route)
    if len(normalized) < 2 or normalized[0] != 0 or normalized[-1] != 0:
        raise InfeasibleSolutionError("A route must start and end at depot 0.")
    markets = normalized[1:-1]
    if any(node <= 0 or node >= instance.node_count for node in markets):
        raise InfeasibleSolutionError("A route contains an invalid market index.")
    if len(set(markets)) != len(markets):
        raise InfeasibleSolutionError("A route cannot visit the same market twice.")
    return normalized


def route_nodes(route: Sequence[int]) -> set[int]:
    """Return the unique nodes in a route, including the depot once."""

    return set(route)


def covered_items(instance: TPPInstance, route: Sequence[int]) -> set[int]:
    markets = set(validate_route(instance, route)[1:-1])
    return {
        item
        for item in instance.items
        if any(instance.sells(market, item) for market in markets)
    }


def missing_items(instance: TPPInstance, route: Sequence[int]) -> set[int]:
    return set(instance.items) - covered_items(instance, route)


def travel_cost(instance: TPPInstance, route: Sequence[int]) -> float:
    normalized = validate_route(instance, route)
    return sum(
        instance.travel_costs[start][end]
        for start, end in zip(normalized, normalized[1:])
    )


def best_purchase_assignment(
    instance: TPPInstance, route: Sequence[int]
) -> tuple[tuple[int, ...], float]:
    normalized = validate_route(instance, route)
    markets = normalized[1:-1]
    assignment: list[int] = []
    total = 0.0
    for item in instance.items:
        choices = [
            (instance.purchase_costs[market][item], market)
            for market in markets
            if instance.purchase_costs[market][item] is not None
        ]
        if not choices:
            raise InfeasibleSolutionError(f"Route does not cover item {item + 1}.")
        price, market = min(choices, key=lambda pair: (pair[0], pair[1]))
        assignment.append(market)
        total += float(price)
    return tuple(assignment), total


def build_solution(instance: TPPInstance, route: Sequence[int]) -> Solution:
    normalized = validate_route(instance, route)
    assignment, purchase = best_purchase_assignment(instance, normalized)
    return Solution(
        route=normalized,
        item_markets=assignment,
        travel_cost=travel_cost(instance, normalized),
        purchase_cost=purchase,
    )


def is_strictly_better(candidate: Solution, incumbent: Solution) -> bool:
    return candidate.total_cost < incumbent.total_cost - EPSILON


def choose_best(solutions: Iterable[Solution]) -> Solution:
    """Select the cheapest solution with deterministic route tie-breaking."""

    values = list(solutions)
    if not values:
        raise ValueError("At least one solution is required.")
    return min(values, key=lambda solution: (solution.total_cost, solution.route))


def assert_solution_consistent(instance: TPPInstance, solution: Solution) -> None:
    rebuilt = build_solution(instance, solution.route)
    if rebuilt.item_markets != solution.item_markets:
        raise AssertionError("Purchase assignment is inconsistent with the route.")
    for actual, expected, name in (
        (solution.travel_cost, rebuilt.travel_cost, "travel cost"),
        (solution.purchase_cost, rebuilt.purchase_cost, "purchase cost"),
        (solution.total_cost, rebuilt.total_cost, "total cost"),
    ):
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=EPSILON):
            raise AssertionError(f"Stored {name} is inconsistent with the route.")
