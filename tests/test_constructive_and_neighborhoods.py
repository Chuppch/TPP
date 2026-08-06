from __future__ import annotations

import unittest

from tpp.core.local_solution.constructive import constructive_heuristic
from tpp.core.local_solution.neighborhoods import Neighborhood, best_neighbor, explore
from tpp.domain.evaluation import assert_solution_consistent, build_solution

from tests.fixtures import paper_instance


class ConstructiveAndNeighborhoodTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = paper_instance()

    def test_constructive_heuristic_selects_maximum_item_coverage(self) -> None:
        solution = constructive_heuristic(self.instance)
        # Market 4 is the only market covering all three missing items, so
        # Algorithm 2 selects it even though the later ILS-RC optimum is 121.
        self.assertEqual(solution.route, (0, 4, 0))
        self.assertEqual(solution.total_cost, 122)

    def test_all_best_neighbors_are_feasible_and_non_worsening(self) -> None:
        solution = build_solution(self.instance, (0, 1, 2, 3, 4, 0))
        for neighborhood in Neighborhood:
            with self.subTest(neighborhood=neighborhood.value):
                candidate = best_neighbor(self.instance, solution, neighborhood)
                self.assertLessEqual(candidate.total_cost, solution.total_cost)
                assert_solution_consistent(self.instance, candidate)

    def test_move_and_switch_preserve_the_market_set(self) -> None:
        solution = build_solution(self.instance, (0, 1, 2, 3, 4, 0))
        for neighborhood in (Neighborhood.MOVE, Neighborhood.SWITCH):
            candidate = best_neighbor(self.instance, solution, neighborhood)
            self.assertEqual(set(candidate.visited_markets), set(solution.visited_markets))
            self.assertEqual(candidate.purchase_cost, solution.purchase_cost)

    def test_explore_zero_searches_returns_original(self) -> None:
        solution = build_solution(self.instance, (0, 1, 2, 3, 4, 0))
        self.assertIs(explore(self.instance, solution, Neighborhood.DROP, 0), solution)


if __name__ == "__main__":
    unittest.main()
