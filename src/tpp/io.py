"""JSON input and output helpers for small CPU-only TPP experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .domain.model import ILSResult, Solution, TPPInstance


def instance_from_dict(data: dict[str, Any]) -> TPPInstance:
    try:
        name = str(data.get("name", "unnamed"))
        travel_costs = data["travel_costs"]
        market_purchase_costs = data["market_purchase_costs"]
    except KeyError as exc:
        raise ValueError(f"Missing required JSON field: {exc.args[0]}") from exc
    return TPPInstance.from_market_matrices(name, travel_costs, market_purchase_costs)


def load_instance(path: str | Path) -> TPPInstance:
    source = Path(path)
    with source.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("Instance JSON root must be an object.")
    return instance_from_dict(data)


def format_solution(solution: Solution) -> str:
    assignments = ", ".join(
        f"item {item + 1}->market {market}"
        for item, market in enumerate(solution.item_markets)
    )
    return "\n".join(
        (
            f"route: {' -> '.join(map(str, solution.route))}",
            f"purchases: {assignments}",
            f"travel_cost: {solution.travel_cost:g}",
            f"purchase_cost: {solution.purchase_cost:g}",
            f"total_cost: {solution.total_cost:g}",
        )
    )


def format_result(result: ILSResult) -> str:
    return "\n".join(
        (
            format_solution(result.solution),
            f"iterations: {result.iterations}",
            f"perturbations: {result.perturbations}",
            f"diversity_restarts: {result.diversity_restarts}",
            f"seed: {result.seed}",
            f"elapsed_seconds: {result.elapsed_seconds:.6f}",
        )
    )


def result_as_json(result: ILSResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
