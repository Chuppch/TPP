from __future__ import annotations

import unittest

from tpp.core.ils_engine.ils import solve
from tpp.domain.evaluation import assert_solution_consistent
from tpp.exact import exact_solve
from tpp.domain.model import ILSConfig, TPPInstance

from tests.fixtures import paper_instance, random_instance


class ILSAndExactTests(unittest.TestCase):
    def test_exact_solver_finds_paper_optimum(self) -> None:
        solution = exact_solve(paper_instance())
        self.assertEqual(solution.route, (0, 3, 2, 0))
        self.assertEqual(solution.total_cost, 121)

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

    def test_exact_solver_rejects_more_than_eight_markets(self) -> None:
        market_count = 9
        node_count = market_count + 1
        travel = [
            [0 if start == end else 1 for end in range(node_count)]
            for start in range(node_count)
        ]
        prices = [[1] for _ in range(market_count)]
        instance = TPPInstance.from_market_matrices("too-large-for-exact", travel, prices)
        with self.assertRaises(ValueError):
            exact_solve(instance)


if __name__ == "__main__":
    unittest.main()
