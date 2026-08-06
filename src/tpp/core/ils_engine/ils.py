"""Algorithm 9: Iterated Local Search with Route Configuration."""

from __future__ import annotations

import random
import time

from ..local_solution.constructive import constructive_heuristic
from .diversity import DiversityMemory, diversity_constructive_heuristic
from ...domain.evaluation import is_strictly_better
from ..local_solution.local_search import local_search
from ...domain.model import ILSConfig, ILSResult, TPPInstance
from .perturbation import destroy, repair
from ..local_solution.route_configuration import route_configuration


def solve(instance: TPPInstance, config: ILSConfig | None = None) -> ILSResult:
    """Run the Section 2 ILS-RC algorithm on a CPU-safe instance."""

    params = config or ILSConfig()
    started = time.perf_counter()
    rng = random.Random(params.seed)
    memory = DiversityMemory.empty(instance.node_count)

    x = constructive_heuristic(instance)
    memory.record(x.route)
    x = route_configuration(
        instance,
        x,
        params.delta_add,
        params.delta_drop,
        params.delta_exchange,
    )
    x = local_search(instance, x)
    incumbent = x
    no_improvement = 0
    perturbations = 0
    diversity_restarts = 0

    for _iteration in range(1, params.k_max + 1):
        if no_improvement == params.lambda_max:
            x = diversity_constructive_heuristic(instance, memory)
            no_improvement = 0
            diversity_restarts += 1
        else:
            x = repair(instance, destroy(x, params.alpha, rng), memory)
            perturbations += 1
        memory.record(x.route)

        x = route_configuration(
            instance,
            x,
            params.delta_add,
            params.delta_drop,
            params.delta_exchange,
        )
        x = local_search(instance, x)

        if is_strictly_better(x, incumbent):
            incumbent = x
            no_improvement = 0
        else:
            no_improvement += 1

    return ILSResult(
        solution=incumbent,
        iterations=params.k_max,
        perturbations=perturbations,
        diversity_restarts=diversity_restarts,
        seed=params.seed,
        elapsed_seconds=time.perf_counter() - started,
    )
