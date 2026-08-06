from __future__ import annotations

import unittest

from tpp.domain.evaluation import (
    InfeasibleSolutionError,
    assert_solution_consistent,
    build_solution,
)
from tpp.domain.model import InstanceValidationError, TPPInstance

from tests.fixtures import paper_instance


class ModelAndEvaluationTests(unittest.TestCase):
    def test_paper_route_cost_breakdown(self) -> None:
        instance = paper_instance()
        solution = build_solution(instance, (0, 3, 2, 0))
        self.assertEqual(solution.item_markets, (3, 2, 3))
        self.assertEqual(solution.travel_cost, 57)
        self.assertEqual(solution.purchase_cost, 64)
        self.assertEqual(solution.total_cost, 121)
        assert_solution_consistent(instance, solution)

    def test_asymmetric_reverse_route_has_different_cost(self) -> None:
        instance = paper_instance()
        forward = build_solution(instance, (0, 3, 2, 0))
        reverse = build_solution(instance, (0, 2, 3, 0))
        self.assertEqual(forward.travel_cost, 57)
        self.assertEqual(reverse.travel_cost, 81)
        self.assertEqual(reverse.total_cost, 145)

    def test_route_must_cover_every_item(self) -> None:
        with self.assertRaises(InfeasibleSolutionError):
            build_solution(paper_instance(), (0, 1, 0))

    def test_route_cannot_repeat_a_market(self) -> None:
        with self.assertRaises(InfeasibleSolutionError):
            build_solution(paper_instance(), (0, 3, 3, 2, 0))

    def test_instance_rejects_an_unavailable_item(self) -> None:
        with self.assertRaises(InstanceValidationError):
            TPPInstance.from_market_matrices(
                "invalid",
                [[0, 1], [1, 0]],
                [[None]],
            )


if __name__ == "__main__":
    unittest.main()
