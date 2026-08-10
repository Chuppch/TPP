from __future__ import annotations

import random
import unittest

from tpp.core.ils_engine.diversity import DiversityMemory, diversity_constructive_heuristic
from tpp.core.ils_engine.perturbation import destroy, repair
from tpp.core.local_solution.constructive import constructive_heuristic
from tpp.domain.evaluation import assert_solution_consistent, build_solution

from tests.fixtures import paper_instance


class PerturbationAndDiversityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = paper_instance()

    def test_destroy_removes_rounded_up_fraction(self) -> None:
        solution = build_solution(self.instance, (0, 1, 2, 3, 4, 0))
        destroyed = destroy(solution, 0.26, random.Random(7))
        self.assertEqual(len(solution.visited_markets) - (len(destroyed) - 2), 2)

    def test_repair_restores_feasibility(self) -> None:
        solution = build_solution(self.instance, (0, 1, 2, 3, 4, 0))
        memory = DiversityMemory.empty(self.instance.node_count)
        memory.record(solution.route)
        destroyed = destroy(solution, 0.5, random.Random(3))
        repaired = repair(self.instance, destroyed, memory)
        assert_solution_consistent(self.instance, repaired)

    def test_diversity_memory_is_symmetric_and_includes_depot(self) -> None:
        memory = DiversityMemory.empty(self.instance.node_count)
        memory.record((0, 3, 2, 0))
        self.assertEqual(memory.counts[0][3], 1)
        self.assertEqual(memory.counts[3][0], 1)
        self.assertEqual(memory.counts[2][3], memory.counts[3][2])

    def test_diversity_constructive_returns_feasible_solution(self) -> None:
        memory = DiversityMemory.empty(self.instance.node_count)
        memory.record(constructive_heuristic(self.instance).route)
        solution = diversity_constructive_heuristic(self.instance, memory)
        assert_solution_consistent(self.instance, solution)


if __name__ == "__main__":
    unittest.main()
