from app.research.marker_sync import MarkerSynchronizer
from app.research.ring_buffer import EEGRingBuffer


class TestEEGRingBuffer:
    def test_push_and_available(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=2)
        assert buf.available == 0
        buf.push([1.0, 2.0], timestamp=0.0)
        assert buf.available == 1

    def test_max_capacity(self):
        buf = EEGRingBuffer(max_samples=10, n_channels=1)
        for i in range(20):
            buf.push([float(i)], timestamp=float(i))
        assert buf.available == 10
        assert buf.stats.total_received == 20
        assert buf.stats.total_dropped == 10

    def test_get_window(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=1)
        for i in range(10):
            buf.push([float(i)], timestamp=float(i))

        samples, timestamps = buf.get_window(5)
        assert len(samples) == 5
        assert samples[0] == [5.0]
        assert samples[-1] == [9.0]
        assert buf.available == 10

    def test_get_and_clear(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=1)
        for i in range(10):
            buf.push([float(i)])

        samples, _ = buf.get_and_clear(5)
        assert len(samples) == 5
        assert buf.available == 5

    def test_push_chunk(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=2)
        chunk = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        buf.push_chunk(chunk)
        assert buf.available == 3

    def test_clear(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=1)
        for i in range(5):
            buf.push([float(i)])
        buf.clear()
        assert buf.available == 0

    def test_is_full(self):
        buf = EEGRingBuffer(max_samples=5, n_channels=1)
        for i in range(5):
            buf.push([float(i)])
        assert buf.is_full

    def test_signal_quality_empty(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=1)
        q = buf.signal_quality_estimate()
        assert q["quality"] == 0.0
        assert q["status"] == "empty"

    def test_signal_quality_good(self):
        buf = EEGRingBuffer(max_samples=1000, n_channels=2)
        for i in range(100):
            buf.push([float(i), float(i) * 0.5], timestamp=float(i) / 256.0)
        q = buf.signal_quality_estimate()
        assert q["quality"] > 0.5
        assert q["status"] in ("good", "degraded")
        assert q["available_samples"] == 100

    def test_signal_quality_flat_detection(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=2)
        for _ in range(20):
            buf.push([0.0, 5.0], timestamp=0.1)
        q = buf.signal_quality_estimate()
        assert q["flat_channels"] == 2

    def test_drop_rate(self):
        buf = EEGRingBuffer(max_samples=5, n_channels=1)
        for i in range(10):
            buf.push([float(i)])
        assert buf.stats.drop_rate == 0.5

    def test_window_larger_than_available(self):
        buf = EEGRingBuffer(max_samples=100, n_channels=1)
        buf.push([1.0])
        buf.push([2.0])
        samples, _ = buf.get_window(10)
        assert len(samples) == 2


class TestMarkerSynchronizer:
    def test_add_marker(self):
        sync = MarkerSynchronizer()
        m = sync.add_marker("trial", "trial_start", metadata={"trial_index": 0})
        assert m.marker_type == "trial"
        assert m.label == "trial_start"
        assert sync.marker_count == 1

    def test_start_session(self):
        sync = MarkerSynchronizer()
        sync.start_session(lsl_time=100.0)
        assert sync.marker_count == 1
        markers = sync.get_markers()
        assert markers[0]["label"] == "session_start"

    def test_mark_trial_start_end(self):
        sync = MarkerSynchronizer()
        sync.mark_trial_start(0, stimulus_id="corridor_simple")
        sync.mark_trial_end(0)
        trial_markers = sync.get_trial_markers(0)
        assert len(trial_markers) == 2
        labels = [m["label"] for m in trial_markers]
        assert "trial_start" in labels
        assert "trial_end" in labels

    def test_mark_stimulus_onset(self):
        sync = MarkerSynchronizer()
        m = sync.mark_stimulus_onset("corridor_simple", trial_index=0)
        assert m.label == "stimulus_onset"
        assert m.metadata["stimulus_id"] == "corridor_simple"

    def test_mark_self_report(self):
        sync = MarkerSynchronizer()
        m = sync.mark_self_report(0, {"vividness": 5})
        assert m.metadata["report"]["vividness"] == 5

    def test_filter_by_type(self):
        sync = MarkerSynchronizer()
        sync.add_marker("trial", "trial_start")
        sync.add_marker("stimulus", "stimulus_onset")
        sync.add_marker("trial", "trial_end")
        trial_only = sync.get_markers(marker_type="trial")
        assert len(trial_only) == 2

    def test_export_markers(self):
        sync = MarkerSynchronizer()
        sync.start_session()
        sync.mark_trial_start(0)
        exported = sync.export_markers()
        assert len(exported) == 2
        assert all("marker_type" in m for m in exported)
        assert all("timestamp_local" in m for m in exported)

    def test_clear(self):
        sync = MarkerSynchronizer()
        sync.add_marker("trial", "trial_start")
        sync.clear()
        assert sync.marker_count == 0

    def test_clock_offset(self):
        sync = MarkerSynchronizer()
        sync.start_session(lsl_time=1000.0)
        m = sync.add_marker("test", "test_marker")
        assert m.timestamp_lsl > 0
