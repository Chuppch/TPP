from __future__ import annotations

import unittest

from tpp.core.local_solution.local_search import local_search
from tpp.core.local_solution.neighborhoods import Neighborhood, best_neighbor
from tpp.core.local_solution.route_configuration import route_configuration
from tpp.domain.evaluation import build_solution

from tests.fixtures import paper_instance


class RouteAndLocalSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = paper_instance()

    def test_route_configuration_is_non_worsening_and_drop_optimal(self) -> None:
        initial = build_solution(self.instance, (0, 1, 2, 3, 4, 0))
        configured = route_configuration(self.instance, initial, 1, 1, 1)
        self.assertLessEqual(configured.total_cost, initial.total_cost)
        drop_candidate = best_neighbor(self.instance, configured, Neighborhood.DROP)
        self.assertEqual(drop_candidate.total_cost, configured.total_cost)

    def test_local_search_changes_only_route_order(self) -> None:
        initial = build_solution(self.instance, (0, 2, 3, 0))
        improved = local_search(self.instance, initial)
        self.assertEqual(set(improved.visited_markets), set(initial.visited_markets))
        self.assertEqual(improved.purchase_cost, initial.purchase_cost)
        self.assertLessEqual(improved.travel_cost, initial.travel_cost)
        self.assertEqual(improved.route, (0, 3, 2, 0))


if __name__ == "__main__":
    unittest.main()
