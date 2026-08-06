"""Algorithm 4: route configuration."""

from __future__ import annotations

from ...domain.model import Solution, TPPInstance
from .neighborhoods import Neighborhood, explore


def route_configuration(
    instance: TPPInstance,
    solution: Solution,
    delta_add: int,
    delta_drop: int,
    delta_exchange: int,
) -> Solution:
    current = explore(instance, solution, Neighborhood.ADD, delta_add)
    current = explore(instance, current, Neighborhood.DROP, delta_drop)
    current = explore(instance, current, Neighborhood.EXCHANGE, delta_exchange)
    current = explore(instance, current, Neighborhood.DROP, None)
    return current
