"""Core immutable data structures for UTPP instances and solutions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


MAX_TOTAL_NODES = 50
MAX_ILS_ITERATIONS = 1000
MAX_EXACT_MARKETS = 8


class InstanceValidationError(ValueError):
    """Raised when a TPP instance violates the supported model."""


@dataclass(frozen=True)
class TPPInstance:
    """A complete directed UTPP instance.

    ``travel_costs[i][j]`` is the directed cost from node ``i`` to node
    ``j``. ``purchase_costs[i][k]`` is the price of item ``k`` at market
    ``i``; ``None`` means the item is unavailable. Node 0 is always the
    depot and cannot sell items.
    """

    name: str
    travel_costs: tuple[tuple[float, ...], ...]
    purchase_costs: tuple[tuple[Optional[float], ...], ...]

    def __post_init__(self) -> None:
        node_count = len(self.travel_costs)
        if node_count < 2:
            raise InstanceValidationError("An instance needs a depot and at least one market.")
        if node_count > MAX_TOTAL_NODES:
            raise InstanceValidationError(
                f"CPU safety limit exceeded: {node_count} nodes > {MAX_TOTAL_NODES}."
            )
        if any(len(row) != node_count for row in self.travel_costs):
            raise InstanceValidationError("Travel cost matrix must be square.")
        for row in self.travel_costs:
            for cost in row:
                if not isinstance(cost, (int, float)) or isinstance(cost, bool):
                    raise InstanceValidationError("Travel costs must be numeric.")
                if cost < 0:
                    raise InstanceValidationError("Travel costs must be non-negative.")

        if len(self.purchase_costs) != node_count:
            raise InstanceValidationError("Purchase matrix must have one row per node.")
        if not self.purchase_costs or not self.purchase_costs[0]:
            raise InstanceValidationError("An instance needs at least one item.")
        item_count = len(self.purchase_costs[0])
        if any(len(row) != item_count for row in self.purchase_costs):
            raise InstanceValidationError("Purchase matrix rows must have equal length.")
        if any(price is not None for price in self.purchase_costs[0]):
            raise InstanceValidationError("The depot cannot sell items.")
        for market in range(1, node_count):
            for price in self.purchase_costs[market]:
                if price is not None:
                    if not isinstance(price, (int, float)) or isinstance(price, bool):
                        raise InstanceValidationError("Purchase prices must be numeric or null.")
                    if price < 0:
                        raise InstanceValidationError("Purchase prices must be non-negative.")

        for item in range(item_count):
            if not any(self.purchase_costs[market][item] is not None for market in self.markets):
                raise InstanceValidationError(f"Item {item + 1} is unavailable in every market.")

    @classmethod
    def from_market_matrices(
        cls,
        name: str,
        travel_costs: Sequence[Sequence[float]],
        market_purchase_costs: Sequence[Sequence[Optional[float]]],
    ) -> "TPPInstance":
        """Build an instance from a travel matrix and market-by-item prices.

        ``market_purchase_costs`` omits the depot row and therefore contains
        exactly ``len(travel_costs) - 1`` rows.
        """

        travel = tuple(tuple(float(value) for value in row) for row in travel_costs)
        if len(market_purchase_costs) != len(travel) - 1:
            raise InstanceValidationError(
                "Market purchase matrix must omit the depot and contain one row per market."
            )
        if not market_purchase_costs or not market_purchase_costs[0]:
            raise InstanceValidationError("An instance needs at least one item.")
        item_count = len(market_purchase_costs[0])
        depot_row: tuple[Optional[float], ...] = tuple(None for _ in range(item_count))
        market_rows = tuple(
            tuple(None if value is None else float(value) for value in row)
            for row in market_purchase_costs
        )
        return cls(name=name, travel_costs=travel, purchase_costs=(depot_row, *market_rows))

    @property
    def node_count(self) -> int:
        return len(self.travel_costs)

    @property
    def market_count(self) -> int:
        return self.node_count - 1

    @property
    def item_count(self) -> int:
        return len(self.purchase_costs[0])

    @property
    def markets(self) -> tuple[int, ...]:
        return tuple(range(1, self.node_count))

    @property
    def items(self) -> tuple[int, ...]:
        return tuple(range(self.item_count))

    def sells(self, market: int, item: int) -> bool:
        return self.purchase_costs[market][item] is not None


@dataclass(frozen=True)
class Solution:
    """A feasible TPP route with its cheapest purchase assignment."""

    route: tuple[int, ...]
    item_markets: tuple[int, ...]
    travel_cost: float
    purchase_cost: float

    @property
    def total_cost(self) -> float:
        return self.travel_cost + self.purchase_cost

    @property
    def visited_markets(self) -> tuple[int, ...]:
        return self.route[1:-1]

    def to_dict(self) -> dict[str, object]:
        return {
            "route": list(self.route),
            "visited_markets": list(self.visited_markets),
            "item_markets": [market for market in self.item_markets],
            "travel_cost": self.travel_cost,
            "purchase_cost": self.purchase_cost,
            "total_cost": self.total_cost,
        }


@dataclass(frozen=True)
class ILSConfig:
    """Algorithm 9 parameters plus a deterministic random seed."""

    k_max: int = 100
    lambda_max: int = 20
    delta_add: int = 1
    delta_drop: int = 1
    delta_exchange: int = 1
    alpha: float = 0.2
    seed: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.k_max <= MAX_ILS_ITERATIONS:
            raise ValueError(f"k_max must be between 0 and {MAX_ILS_ITERATIONS}.")
        if not 0 <= self.lambda_max <= MAX_ILS_ITERATIONS:
            raise ValueError("lambda_max must be non-negative and within the CPU safety limit.")
        for name, value in (
            ("delta_add", self.delta_add),
            ("delta_drop", self.delta_drop),
            ("delta_exchange", self.delta_exchange),
        ):
            if not 0 <= value <= MAX_ILS_ITERATIONS:
                raise ValueError(f"{name} must be non-negative and within the safety limit.")
        if not 0 < self.alpha <= 1:
            raise ValueError("alpha must be in the interval (0, 1].")


@dataclass(frozen=True)
class ILSResult:
    """Best solution and reproducibility metadata from Algorithm 9."""

    solution: Solution
    iterations: int
    perturbations: int
    diversity_restarts: int
    seed: int
    elapsed_seconds: float

    def to_dict(self) -> dict[str, object]:
        result = self.solution.to_dict()
        result.update(
            {
                "iterations": self.iterations,
                "perturbations": self.perturbations,
                "diversity_restarts": self.diversity_restarts,
                "seed": self.seed,
                "elapsed_seconds": self.elapsed_seconds,
            }
        )
        return result
