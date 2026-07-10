from app.research.feedback_conditions import (
    FixedFeedbackPolicy,
    YokedFeedbackPolicy,
    get_feedback_policy,
)
from app.research.provenance import build_provenance_record, hash_trial_data
from app.research.stimulus_registry import (
    StimulusEntry,
    get_stimulus,
    list_stimuli,
    list_stimulus_ids,
    register_stimulus,
)
from app.research.trial_scheduler import TrialScheduler, TrialSpec
from app.schemas.research import FeedbackCondition


class TestFixedFeedbackPolicy:
    def test_constant_output(self):
        policy = FixedFeedbackPolicy(level=3)
        fb1 = policy.compute("s1", 0)
        fb2 = policy.compute("s1", 5)
        fb3 = policy.compute("s1", 10)
        assert fb1.scene_clarity == fb2.scene_clarity == fb3.scene_clarity
        assert fb1.blur == fb2.blur == fb3.blur
        assert fb1.fog_density == fb2.fog_density == fb3.fog_density

    def test_different_levels_differ(self):
        p1 = FixedFeedbackPolicy(level=1)
        p8 = FixedFeedbackPolicy(level=8)
        fb1 = p1.compute("s1", 0)
        fb8 = p8.compute("s1", 0)
        assert fb1.scene_clarity != fb8.scene_clarity

    def test_session_id_propagates(self):
        policy = FixedFeedbackPolicy(level=3)
        fb = policy.compute("test-session-123", 0)
        assert fb.session_id == "test-session-123"

    def test_reason_contains_fixed(self):
        policy = FixedFeedbackPolicy(level=5)
        fb = policy.compute("s1", 0)
        assert "fixed_feedback" in fb.reason


class TestYokedFeedbackPolicy:
    def test_replays_sequence(self):
        sequence = [
            {"scene_clarity": 0.7, "blur": 0.1},
            {"scene_clarity": 0.5, "blur": 0.3},
        ]
        policy = YokedFeedbackPolicy(sequence)
        fb0 = policy.compute("s1", 0)
        fb1 = policy.compute("s1", 1)
        assert fb0.scene_clarity == 0.7
        assert fb1.scene_clarity == 0.5

    def test_clamps_to_last(self):
        sequence = [{"scene_clarity": 0.8}]
        policy = YokedFeedbackPolicy(sequence)
        fb5 = policy.compute("s1", 5)
        assert fb5.scene_clarity == 0.8

    def test_empty_sequence_defaults(self):
        policy = YokedFeedbackPolicy([])
        fb = policy.compute("s1", 0)
        assert fb.scene_clarity == 0.5

    def test_reason_yoked(self):
        policy = YokedFeedbackPolicy([{"scene_clarity": 0.5}])
        fb = policy.compute("s1", 0)
        assert fb.reason == "yoked_feedback"


class TestGetFeedbackPolicy:
    def test_adaptive_returns_engine(self):
        from app.services.feedback_policy_engine import FeedbackPolicyEngine

        policy = get_feedback_policy(FeedbackCondition.ADAPTIVE)
        assert isinstance(policy, FeedbackPolicyEngine)

    def test_fixed_returns_fixed(self):
        policy = get_feedback_policy(FeedbackCondition.FIXED, level=4)
        assert isinstance(policy, FixedFeedbackPolicy)

    def test_yoked_returns_yoked(self):
        policy = get_feedback_policy(
            FeedbackCondition.YOKED,
            replay_sequence=[{"scene_clarity": 0.5}],
        )
        assert isinstance(policy, YokedFeedbackPolicy)


class TestTrialSpec:
    def test_initial_state(self):
        spec = TrialSpec(trial_index=0, stimulus_id="corridor_simple")
        assert spec.status == "pending"
        assert spec.started_at is None
        assert spec.ended_at is None

    def test_start_sets_running(self):
        spec = TrialSpec(trial_index=0, stimulus_id="corridor_simple")
        spec.start()
        assert spec.status == "running"
        assert spec.started_at is not None

    def test_complete_sets_completed(self):
        spec = TrialSpec(trial_index=0, stimulus_id="corridor_simple")
        spec.start()
        spec.complete()
        assert spec.status == "completed"
        assert spec.ended_at is not None

    def test_to_dict(self):
        spec = TrialSpec(trial_index=2, stimulus_id="corridor_doors")
        d = spec.to_dict()
        assert d["trial_index"] == 2
        assert d["stimulus_id"] == "corridor_doors"
        assert "trial_id" in d


class TestTrialScheduler:
    def test_creates_correct_number_of_trials(self):
        scheduler = TrialScheduler(
            condition=FeedbackCondition.ADAPTIVE,
            stimulus_ids=["corridor_simple", "corridor_detailed"],
            trials_per_session=5,
        )
        assert len(scheduler.all_trials()) == 5

    def test_cycles_through_stimuli(self):
        scheduler = TrialScheduler(
            condition=FeedbackCondition.ADAPTIVE,
            stimulus_ids=["a", "b"],
            trials_per_session=4,
        )
        trials = scheduler.all_trials()
        stim_ids = [t["stimulus_id"] for t in trials]
        assert stim_ids == ["a", "b", "a", "b"]

    def test_start_and_complete_flow(self):
        scheduler = TrialScheduler(
            condition=FeedbackCondition.FIXED,
            stimulus_ids=["corridor_simple"],
            trials_per_session=3,
        )
        assert scheduler.has_next()

        t1 = scheduler.start_trial()
        assert t1 is not None
        assert t1.status == "running"

        t1_done = scheduler.complete_trial()
        assert t1_done is not None
        assert t1_done.status == "completed"
        assert scheduler.completed_count() == 1

        scheduler.start_trial()
        scheduler.complete_trial()
        scheduler.start_trial()
        scheduler.complete_trial()
        assert scheduler.completed_count() == 3
        assert not scheduler.has_next()

    def test_total_estimated_duration(self):
        scheduler = TrialScheduler(
            condition=FeedbackCondition.ADAPTIVE,
            stimulus_ids=["corridor_simple"],
            trials_per_session=3,
            trial_duration_s=120.0,
            iti_s=30.0,
        )
        expected = 3 * 120.0 + 2 * 30.0
        assert scheduler.total_estimated_duration_s() == expected


class TestStimulusRegistry:
    def test_list_stimuli(self):
        stimuli = list_stimuli()
        assert len(stimuli) >= 5
        ids = {s.stimulus_id for s in stimuli}
        assert "corridor_simple" in ids
        assert "corridor_detailed" in ids

    def test_get_stimulus(self):
        s = get_stimulus("corridor_simple")
        assert s is not None
        assert s.name == "Simple Corridor"
        assert len(s.content_hash) == 16

    def test_unknown_returns_none(self):
        assert get_stimulus("nonexistent_stimulus") is None

    def test_list_ids(self):
        ids = list_stimulus_ids()
        assert "corridor_simple" in ids

    def test_register_custom(self):
        entry = StimulusEntry(
            stimulus_id="test_custom",
            name="Test Custom",
            category="test",
            description="Test stimulus",
            content_hash="abc123",
        )
        register_stimulus(entry)
        assert get_stimulus("test_custom") is not None

    def test_content_hash_stable(self):
        s1 = get_stimulus("corridor_simple")
        s2 = get_stimulus("corridor_simple")
        assert s1 is not None and s2 is not None
        assert s1.content_hash == s2.content_hash


class TestProvenance:
    def test_build_record(self):
        record = build_provenance_record(
            study_id="study-1",
            participant_id="p-1",
            session_id="s-1",
            condition="adaptive",
            trial_index=0,
            stimulus_id="corridor_simple",
            signal_provider_id="simulated.default",
            protocol_version="1.0",
        )
        assert record["study_id"] == "study-1"
        assert record["condition"] == "adaptive"
        assert record["provenance_version"] == "1.0"
        assert "timestamp" in record
        assert "git_sha" in record

    def test_hash_deterministic(self):
        data = {"a": 1, "b": "test"}
        h1 = hash_trial_data(data)
        h2 = hash_trial_data(data)
        assert h1 == h2
        assert len(h1) == 32

    def test_hash_differs_for_different_data(self):
        h1 = hash_trial_data({"a": 1})
        h2 = hash_trial_data({"a": 2})
        assert h1 != h2
