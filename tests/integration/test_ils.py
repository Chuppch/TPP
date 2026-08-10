from __future__ import annotations

import unittest

from tpp.core.ils_engine.ils import solve
from tpp.domain.evaluation import assert_solution_consistent
from tpp.domain.model import ILSConfig
from tpp.exact import exact_solve

from tests.fixtures import paper_instance, random_instance


class ILSIntegrationTests(unittest.TestCase):
    def test_ils_finds_paper_optimum(self) -> None:
        result = solve(
            paper_instance(),
            ILSConfig(k_max=20, lambda_max=5, alpha=0.5, seed=0),
        )
        self.assertEqual(result.solution.route, (0, 3, 2, 0))
        self.assertEqual(result.solution.total_cost, 121)
        self.assertEqual(result.iterations, 20)

    def test_ils_is_reproducible_with_fixed_seed(self) -> None:
        instance = random_instance(11)
        config = ILSConfig(k_max=25, lambda_max=5, alpha=0.4, seed=19)
        first = solve(instance, config)
        second = solve(instance, config)
        self.assertEqual(first.solution, second.solution)
        self.assertEqual(first.perturbations, second.perturbations)
        self.assertEqual(first.diversity_restarts, second.diversity_restarts)

    def test_heuristic_solution_is_feasible_and_not_better_than_exact_oracle(self) -> None:
        instance = random_instance(5)
        heuristic = solve(
            instance,
            ILSConfig(k_max=30, lambda_max=6, alpha=0.4, seed=5),
        ).solution
        optimum = exact_solve(instance)
        assert_solution_consistent(instance, heuristic)
        self.assertGreaterEqual(heuristic.total_cost, optimum.total_cost)


if __name__ == "__main__":
    unittest.main()
