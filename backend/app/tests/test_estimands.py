"""Tests for causal estimands and identification assumptions."""
from app.research.estimands import (
    ASSUMPTIONS,
    AssumptionStatus,
    build_assumption_report,
    estimand_hash,
    get_confirmatory_estimands,
    get_primary_estimand,
    list_assumptions,
    list_estimands,
)


class TestEstimandRegistry:
    def test_exactly_one_primary(self):
        primary = [e for e in list_estimands() if e.is_primary]
        assert len(primary) == 1

    def test_primary_is_objective(self):
        p = get_primary_estimand()
        assert p.endpoint_id == "composite_reconstruction_error"

    def test_primary_sign_interpretation(self):
        p = get_primary_estimand()
        assert "lower" in p.sign_interpretation.lower() or "negative" in p.sign_interpretation.lower()

    def test_primary_formal_expression(self):
        p = get_primary_estimand()
        assert "E[Y(adaptive)" in p.formal_expression

    def test_confirmatory_count(self):
        conf = get_confirmatory_estimands()
        assert len(conf) >= 3

    def test_all_confirmatory_have_assumptions(self):
        for e in get_confirmatory_estimands():
            assert len(e.assumptions) >= 2, f"{e.estimand_id} has too few assumptions"

    def test_secondary_contrasts_exist(self):
        ids = {e.estimand_id for e in list_estimands()}
        assert "ate_adaptive_vs_fixed" in ids
        assert "ate_fixed_vs_yoked" in ids

    def test_estimand_hash_deterministic(self):
        h1 = estimand_hash()
        h2 = estimand_hash()
        assert h1 == h2


class TestAssumptions:
    def test_required_assumptions_exist(self):
        required = ["consistency", "positivity", "no_leakage", "correct_randomization",
                     "no_carryover", "mar", "stable_endpoint", "blinded_analysis"]
        for a in required:
            assert a in ASSUMPTIONS, f"Missing assumption: {a}"

    def test_structurally_enforced_have_verification(self):
        for a in list_assumptions():
            if a.status == AssumptionStatus.STRUCTURALLY_ENFORCED:
                assert len(a.verification_method) > 10

    def test_assumption_report_complete(self):
        report = build_assumption_report()
        assert len(report) == len(ASSUMPTIONS)
        for entry in report:
            assert "assumption_id" in entry
            assert "status" in entry
            assert "used_by" in entry
            assert isinstance(entry["used_by"], list)

    def test_primary_uses_all_assumptions(self):
        p = get_primary_estimand()
        assert len(p.assumptions) == 8


class TestPopulations:
    def test_primary_is_itt(self):
        from app.research.estimands import AnalysisPopulation
        p = get_primary_estimand()
        assert p.population == AnalysisPopulation.INTENTION_TO_TREAT
