"""Unit tests for K8sWatchLoop and ClusterEvent."""

import asyncio
from datetime import datetime, timezone

import pytest

from src.monitoring.watchloop import ClusterEvent, K8sWatchLoop


# ── ClusterEvent ──────────────────────────────────────────────────────────────

class TestClusterEvent:
    def _make_event(self, **kwargs) -> ClusterEvent:
        defaults = dict(
            event_type="crash_loop",
            severity="critical",
            namespace="default",
            resource_kind="Pod",
            resource_name="web-pod",
            message="CrashLoopBackOff: container crashed 5 times",
        )
        defaults.update(kwargs)
        return ClusterEvent(**defaults)

    def test_to_dict_has_required_fields(self):
        event = self._make_event()
        d = event.to_dict()
        for field in ("event_type", "severity", "namespace", "resource_kind", "resource_name", "message"):
            assert field in d, f"Missing field: {field}"

    def test_to_dict_contains_correct_values(self):
        event = self._make_event(event_type="oom_killed", severity="critical")
        d = event.to_dict()
        assert d["event_type"] == "oom_killed"
        assert d["severity"] == "critical"

    def test_to_dict_detected_at_is_iso_string(self):
        event = self._make_event()
        d = event.to_dict()
        assert isinstance(d["detected_at"], str)
        datetime.fromisoformat(d["detected_at"])

    def test_default_labels_empty_dict(self):
        event = self._make_event()
        assert event.labels == {}

    def test_to_dict_includes_labels(self):
        event = self._make_event(labels={"app": "nginx", "env": "prod"})
        d = event.to_dict()
        assert d["labels"] == {"app": "nginx", "env": "prod"}

    def test_detected_at_defaults_to_utcnow(self):
        before = datetime.now(timezone.utc)
        event = self._make_event()
        after = datetime.now(timezone.utc)
        assert before <= event.detected_at <= after


# ── K8sWatchLoop ──────────────────────────────────────────────────────────────

class TestK8sWatchLoop:
    def test_event_queue_maxsize_100(self):
        loop = K8sWatchLoop()
        assert loop._event_queue.maxsize == 100

    def test_initial_state_not_running(self):
        loop = K8sWatchLoop()
        assert loop._running is False
        assert loop.is_running is False

    def test_custom_interval_is_used(self):
        loop = K8sWatchLoop(interval=60)
        assert loop._base_interval == 60
        assert loop._interval == 60

    def test_failure_threshold_constant(self):
        assert K8sWatchLoop._FAILURE_THRESHOLD == 3

    def test_max_backoff_constant(self):
        assert K8sWatchLoop._MAX_BACKOFF_SECONDS == 600

    async def test_queue_accepts_events_up_to_maxsize(self):
        loop = K8sWatchLoop()
        event = ClusterEvent(
            event_type="crash_loop", severity="critical",
            namespace="ns", resource_kind="Pod",
            resource_name="pod", message="test",
        )
        for _ in range(100):
            loop._event_queue.put_nowait(event)
        assert loop._event_queue.full()

    async def test_queue_raises_full_on_overflow(self):
        loop = K8sWatchLoop()
        event = ClusterEvent(
            event_type="test", severity="info",
            namespace="ns", resource_kind="Pod",
            resource_name="pod", message="test",
        )
        for _ in range(100):
            loop._event_queue.put_nowait(event)
        with pytest.raises(asyncio.QueueFull):
            loop._event_queue.put_nowait(event)

    def test_callback_set_on_init(self):
        async def my_callback(event):
            pass

        loop = K8sWatchLoop(event_callback=my_callback)
        assert loop._event_callback is my_callback

    def test_no_callback_is_none(self):
        loop = K8sWatchLoop()
        assert loop._event_callback is None


# ── Backoff logic (unit test the formula, no K8s needed) ─────────────────────

class TestBackoffLogic:
    """Verify the exponential backoff formula used in _tick()."""

    def _backoff_interval(self, base: int, consecutive_failures: int, threshold: int = 3) -> int:
        """Replicate the backoff formula from watchloop._tick()."""
        max_backoff = K8sWatchLoop._MAX_BACKOFF_SECONDS
        new_interval = min(
            base * (2 ** (consecutive_failures - threshold + 1)),
            max_backoff,
        )
        return new_interval

    def test_first_backoff_doubles_interval(self):
        # consecutive_failures = threshold (3)
        result = self._backoff_interval(base=30, consecutive_failures=3)
        assert result == 60  # 30 * 2^1

    def test_second_backoff_quadruples_interval(self):
        result = self._backoff_interval(base=30, consecutive_failures=4)
        assert result == 120  # 30 * 2^2

    def test_backoff_capped_at_max(self):
        result = self._backoff_interval(base=30, consecutive_failures=100)
        assert result == K8sWatchLoop._MAX_BACKOFF_SECONDS

    def test_backoff_never_exceeds_max(self):
        for n in range(3, 50):
            result = self._backoff_interval(base=30, consecutive_failures=n)
            assert result <= K8sWatchLoop._MAX_BACKOFF_SECONDS
