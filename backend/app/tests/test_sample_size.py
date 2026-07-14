"""Tests for sample-size grid search and Pareto analysis."""
from app.research.sample_size import search_design_grid, sample_size_hash


class TestGridSearch:
    def test_produces_points(self):
        table = search_design_grid(
            n_grid=[12], session_grid=[3], trial_grid=[3],
            n_iterations=5,
        )
        assert len(table.points) >= 1

    def test_point_fields(self):
        table = search_design_grid(
            n_grid=[12], session_grid=[3], trial_grid=[3],
            n_iterations=5,
        )
        pt = table.points[0]
        assert pt.n_participants == 12
        assert pt.total_trials == 12 * 3 * 3 * 4

    def test_deterministic(self):
        t1 = search_design_grid(n_grid=[12], session_grid=[3], trial_grid=[3], n_iterations=5)
        t2 = search_design_grid(n_grid=[12], session_grid=[3], trial_grid=[3], n_iterations=5)
        assert sample_size_hash(t1) == sample_size_hash(t2)

    def test_requirements_in_table(self):
        table = search_design_grid(n_grid=[12], session_grid=[3], trial_grid=[3], n_iterations=5)
        assert "max_type_i" in table.requirements
        assert "min_coverage" in table.requirements
