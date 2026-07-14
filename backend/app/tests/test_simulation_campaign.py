"""Tests for the research-mode simulation campaign."""
from app.research.cognitive_agent import (
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_STRICT_NULL,
)
from app.research.simulation_campaign import (
    CORE_SCENARIOS,
    CampaignResult,
    run_full_campaign,
    run_scenario_campaign,
)


class TestScenarioCampaign:
    def test_basic_run(self):
        ss = run_scenario_campaign(
            "strict_null", SCENARIO_STRICT_NULL,
            total_replicates=15, batch_size=8, n_participants=12,
        )
        assert ss.scenario_id == "strict_null"
        assert ss.total_replicates == 15
        assert ss.n_batches == 2

    def test_oracle_reported(self):
        ss = run_scenario_campaign(
            "strict_null", SCENARIO_STRICT_NULL,
            total_replicates=10, batch_size=10,
        )
        assert ss.oracle_effect is not None
        assert ss.oracle_se is not None

    def test_operating_characteristics(self):
        ss = run_scenario_campaign(
            "medium_adaptive", SCENARIO_MEDIUM_ADAPTIVE,
            total_replicates=10, batch_size=10,
        )
        assert 0.0 <= ss.coverage <= 1.0
        assert 0.0 <= ss.convergence_rate <= 1.0
        assert 0.0 <= ss.fallback_rate <= 1.0
        assert 0.0 <= ss.valid_inference_rate <= 1.0

    def test_checkpoint_callback(self):
        batches: list[dict] = []

        def cb(bs):
            batches.append(bs.to_dict())

        run_scenario_campaign(
            "strict_null", SCENARIO_STRICT_NULL,
            total_replicates=15, batch_size=5,
            checkpoint_callback=cb,
        )
        assert len(batches) == 3


class TestFullCampaign:
    def test_reduced_campaign(self):
        result = run_full_campaign(
            total_replicates=10,
            batch_size=10,
            n_participants=12,
            scenarios={
                "strict_null": SCENARIO_STRICT_NULL,
                "medium_adaptive": SCENARIO_MEDIUM_ADAPTIVE,
            },
        )
        assert isinstance(result, CampaignResult)
        assert result.total_scenarios == 2
        assert result.total_replicates == 20
        assert result.campaign_id.startswith("campaign-")

    def test_all_core_scenarios_listed(self):
        assert len(CORE_SCENARIOS) >= 9

    def test_campaign_results_deterministic(self):
        r1 = run_full_campaign(
            total_replicates=10, batch_size=10, n_participants=12,
            scenarios={"strict_null": SCENARIO_STRICT_NULL},
        )
        r2 = run_full_campaign(
            total_replicates=10, batch_size=10, n_participants=12,
            scenarios={"strict_null": SCENARIO_STRICT_NULL},
        )
        s1 = r1.scenario_summaries["strict_null"]
        s2 = r2.scenario_summaries["strict_null"]
        assert s1.type_i_error == s2.type_i_error
        assert s1.coverage == s2.coverage
        assert s1.bias == s2.bias
        assert s1.oracle_effect == s2.oracle_effect

    def test_null_calibration_checked(self):
        result = run_full_campaign(
            total_replicates=10, batch_size=10,
            scenarios={"strict_null": SCENARIO_STRICT_NULL},
        )
        ss = result.scenario_summaries["strict_null"]
        assert ss.type_i_error is not None
        assert ss.type_i_se is not None


class TestCampaignSerialization:
    def test_to_dict(self):
        result = run_full_campaign(
            total_replicates=10, batch_size=10,
            scenarios={"strict_null": SCENARIO_STRICT_NULL},
        )
        d = result.to_dict()
        assert "campaign_id" in d
        assert "scenario_summaries" in d
        assert "strict_null" in d["scenario_summaries"]
        assert d["total_scenarios"] == 1
