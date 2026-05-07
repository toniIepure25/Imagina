from app.evaluation.cohort_simulator import run_cohort
from app.evaluation.scenario_runner import run_scenario


def test_scenario_runner_executes():
    result = run_scenario("improving_user", windows=10)
    assert result["scenario"] == "improving_user"
    assert len(result["timeline"]) == 10
    assert result["last"]["iqi"] >= 0


def test_cohort_simulator_outputs_aggregates():
    result = run_cohort(n=4, windows=8)
    assert result["n"] == 4
    assert "average_iqi_slope" in result
    assert result["runs"]
