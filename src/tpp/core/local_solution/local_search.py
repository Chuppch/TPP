"""Algorithm 5: local search over MOVE and SWITCH neighborhoods."""

from __future__ import annotations

from ...domain.evaluation import choose_best, is_strictly_better
from ...domain.model import Solution, TPPInstance
from .neighborhoods import Neighborhood, explore


def local_search(instance: TPPInstance, solution: Solution) -> Solution:
    x1 = explore(instance, solution, Neighborhood.MOVE, None)
    x1 = explore(instance, x1, Neighborhood.SWITCH, None)

    x2 = explore(instance, solution, Neighborhood.SWITCH, None)
    x2 = explore(instance, x2, Neighborhood.MOVE, None)

    x3 = solution
    while True:
        previous = x3
        x3 = explore(instance, x3, Neighborhood.SWITCH, 1)
        x3 = explore(instance, x3, Neighborhood.MOVE, 1)
        if not is_strictly_better(x3, previous):
            break

    return choose_best((x1, x2, x3))
