"""Unit tests for API Backend WatchLoop."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models.api_backend import ApiBackendConfig
from src.monitoring.api_watchloop import ApiBackendEvent, ApiBackendWatchLoop


@pytest.fixture
def sample_backend_config():
    """Create a sample API backend configuration."""
    return ApiBackendConfig(
        name="test-api",
        url="https://api.test.com",
        health_path="/health",
        check_interval_seconds=10,
        timeout_seconds=5,
        latency_threshold_ms=500,
        error_rate_threshold=0.05,
        consecutive_failures_threshold=2,
        enabled=True,
        headers={"Authorization": "Bearer test-token"},
        ssl_verify=True,
        tags={"team": "platform"},
    )


@pytest.fixture
def event_callback():
    """Create a mock event callback."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_watchloop_initialization(sample_backend_config, event_callback):
    """Test watchloop initializes correctly."""
    watchloop = ApiBackendWatchLoop(
        backends=[sample_backend_config],
        event_callback=event_callback,
    )

    assert not watchloop.is_running
    assert len(watchloop._backends) == 1
    assert "test-api" in watchloop._backends


@pytest.mark.asyncio
async def test_watchloop_start_stop(sample_backend_config, event_callback):
    """Test watchloop can be started and stopped."""
    watchloop = ApiBackendWatchLoop(
        backends=[sample_backend_config],
        event_callback=event_callback,
    )

    await watchloop.start()
    assert watchloop.is_running

    await watchloop.stop()
    assert not watchloop.is_running


@pytest.mark.asyncio
async def test_successful_health_check(sample_backend_config, event_callback):
    """Test successful health check updates status correctly."""
    watchloop = ApiBackendWatchLoop(
        backends=[sample_backend_config],
        event_callback=event_callback,
    )

    # Mock successful HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        await watchloop._check_backend(sample_backend_config)

    # Verify status was updated
    status = watchloop.get_status("test-api")
    assert status is not None
    assert status["test-api"].is_up is True
    assert status["test-api"].consecutive_failures == 0

    # Verify no event was emitted (healthy state)
    event_callback.assert_not_called()


@pytest.mark.asyncio
async def test_backend_down_detection(sample_backend_config, event_callback):
    """Test backend down event is emitted after consecutive failures."""
    watchloop = ApiBackendWatchLoop(
        backends=[sample_backend_config],
        event_callback=event_callback,
    )

    await watchloop.start()

    # Mock timeout exception
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        # First failure - no event yet (threshold is 2)
        await watchloop._check_backend(sample_backend_config)
        await asyncio.sleep(0.1)  # Allow event processing
        assert event_callback.call_count == 0

        # Second failure - should emit event
        await watchloop._check_backend(sample_backend_config)
        await asyncio.sleep(0.1)  # Allow event processing

    await watchloop.stop()

    # Verify event was emitted
    assert event_callback.call_count >= 1
    call_args = event_callback.call_args_list[0][0]
    event = call_args[0]
    assert isinstance(event, ApiBackendEvent)
    assert event.event_type == "api_backend_down"
    assert event.severity == "critical"
    assert event.endpoint_name == "test-api"


@pytest.mark.asyncio
async def test_high_latency_detection(sample_backend_config, event_callback):
    """Test high latency event is emitted when threshold is exceeded."""
    watchloop = ApiBackendWatchLoop(
        backends=[sample_backend_config],
        event_callback=event_callback,
    )

    await watchloop.start()

    # Mock slow responses
    mock_response = MagicMock()
    mock_response.status_code = 200

    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.6)  # Simulate 600ms latency (threshold is 500ms)
        return mock_response

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=slow_response)

        # Perform 6 checks to build up latency history
        for _ in range(6):
            await watchloop._check_backend(sample_backend_config)
            await asyncio.sleep(0.1)

    await watchloop.stop()

    # Verify high latency event was emitted
    # Check if any call had high_latency event
    high_latency_events = [
        call for call in event_callback.call_args_list
        if call[0][0].event_type == "api_high_latency"
    ]
    assert len(high_latency_events) > 0


@pytest.mark.asyncio
async def test_error_rate_detection(sample_backend_config, event_callback):
    """Test high error rate event is emitted."""
    watchloop = ApiBackendWatchLoop(
        backends=[sample_backend_config],
        event_callback=event_callback,
    )

    await watchloop.start()

    # Mock mix of successful and error responses
    call_count = 0

    async def mixed_responses(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_response = MagicMock()
        # 50% error rate (every other request fails)
        mock_response.status_code = 500 if call_count % 2 == 0 else 200
        return mock_response

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mixed_responses)

        # Perform 10 checks to build up error history
        for _ in range(10):
            await watchloop._check_backend(sample_backend_config)
            await asyncio.sleep(0.1)

    await watchloop.stop()

    # Verify high error rate event was emitted (50% > 5% threshold)
    error_rate_events = [
        call for call in event_callback.call_args_list
        if call[0][0].event_type == "api_high_error_rate"
    ]
    assert len(error_rate_events) > 0


@pytest.mark.asyncio
async def test_disabled_backend_ignored():
    """Test disabled backends are not monitored."""
    config = ApiBackendConfig(
        name="disabled-api",
        url="https://api.test.com",
        enabled=False,
    )

    event_callback = AsyncMock()
    watchloop = ApiBackendWatchLoop(
        backends=[config],
        event_callback=event_callback,
    )

    assert len(watchloop._backends) == 0  # Disabled backends filtered out


@pytest.mark.asyncio
async def test_get_status():
    """Test get_status returns current backend status."""
    config = ApiBackendConfig(
        name="test-api",
        url="https://api.test.com",
    )

    watchloop = ApiBackendWatchLoop(
        backends=[config],
        event_callback=AsyncMock(),
    )

    # Initially, no status
    status = watchloop.get_status("test-api")
    assert status == {}

    # After start, status should be available (once a check runs)
    await watchloop.start()
    await asyncio.sleep(0.2)

    status_all = watchloop.get_status()
    assert isinstance(status_all, dict)

    await watchloop.stop()
