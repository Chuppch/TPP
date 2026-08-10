from __future__ import annotations

import unittest

from tpp.domain.model import TPPInstance
from tpp.exact import exact_solve

from tests.fixtures import paper_instance


class ExactSolverTests(unittest.TestCase):
    def test_exact_solver_finds_paper_optimum(self) -> None:
        solution = exact_solve(paper_instance())
        self.assertEqual(solution.route, (0, 3, 2, 0))
        self.assertEqual(solution.total_cost, 121)

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
