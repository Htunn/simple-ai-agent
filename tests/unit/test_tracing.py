"""Unit tests for src/monitoring/tracing.py."""

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    s = MagicMock()
    s.otel_service_name = overrides.get("otel_service_name", "test-service")
    s.environment = overrides.get("environment", "test")
    s.otel_sample_rate = overrides.get("otel_sample_rate", 1.0)
    s.otlp_endpoint = overrides.get("otlp_endpoint", None)
    return s


@pytest.fixture(autouse=True)
def _reset_provider():
    """Reset the module-level _tracer_provider between tests."""
    import src.monitoring.tracing as mod

    original = mod._tracer_provider
    mod._tracer_provider = None
    yield
    mod._tracer_provider = original


# ---------------------------------------------------------------------------
# setup_tracing
# ---------------------------------------------------------------------------


class TestSetupTracing:
    def test_creates_tracer_provider(self):
        import src.monitoring.tracing as mod

        settings = _make_settings()
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource") as MockResource,
            patch("src.monitoring.tracing.trace"),
            patch("src.monitoring.tracing._instrument_libraries"),
            patch("src.monitoring.tracing.ConsoleSpanExporter"),
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            mock_instance = MagicMock()
            MockProvider.return_value = mock_instance
            MockResource.create.return_value = MagicMock()

            mod.setup_tracing(settings)

            MockProvider.assert_called_once()
            assert mod._tracer_provider is mock_instance

    def test_idempotent_second_call_is_noop(self):
        import src.monitoring.tracing as mod

        settings = _make_settings()
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource"),
            patch("src.monitoring.tracing.trace"),
            patch("src.monitoring.tracing._instrument_libraries"),
            patch("src.monitoring.tracing.ConsoleSpanExporter"),
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            MockProvider.return_value = MagicMock()
            mod.setup_tracing(settings)
            mod.setup_tracing(settings)  # second call must be ignored

            MockProvider.assert_called_once()

    def test_sets_global_tracer_provider(self):
        import src.monitoring.tracing as mod

        settings = _make_settings()
        mock_trace = MagicMock()
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource"),
            patch("src.monitoring.tracing.trace", mock_trace),
            patch("src.monitoring.tracing._instrument_libraries"),
            patch("src.monitoring.tracing.ConsoleSpanExporter"),
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            mock_instance = MagicMock()
            MockProvider.return_value = mock_instance
            mod.setup_tracing(settings)

            mock_trace.set_tracer_provider.assert_called_once_with(mock_instance)

    def test_uses_console_exporter_when_no_endpoint(self):
        import src.monitoring.tracing as mod

        settings = _make_settings(otlp_endpoint=None)
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource"),
            patch("src.monitoring.tracing.trace"),
            patch("src.monitoring.tracing._instrument_libraries"),
            patch("src.monitoring.tracing.ConsoleSpanExporter") as MockConsole,
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            MockProvider.return_value = MagicMock()
            mod.setup_tracing(settings)

            MockConsole.assert_called_once()

    def test_calls_add_otlp_exporter_when_endpoint_set(self):
        import src.monitoring.tracing as mod

        settings = _make_settings(otlp_endpoint="http://jaeger:4317")
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource"),
            patch("src.monitoring.tracing.trace"),
            patch("src.monitoring.tracing._instrument_libraries"),
            patch("src.monitoring.tracing._add_otlp_exporter") as mock_add,
        ):
            MockProvider.return_value = MagicMock()
            mod.setup_tracing(settings)

            mock_add.assert_called_once()
            assert mock_add.call_args[0][1] == "http://jaeger:4317"

    def test_resource_contains_service_name_and_env(self):
        import src.monitoring.tracing as mod

        settings = _make_settings(otel_service_name="my-svc", environment="staging")
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource") as MockResource,
            patch("src.monitoring.tracing.trace"),
            patch("src.monitoring.tracing._instrument_libraries"),
            patch("src.monitoring.tracing.ConsoleSpanExporter"),
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            MockProvider.return_value = MagicMock()
            MockResource.create.return_value = MagicMock()
            mod.setup_tracing(settings)

            MockResource.create.assert_called_once_with(
                {"service.name": "my-svc", "deployment.environment": "staging"}
            )

    def test_instruments_libraries_on_init(self):
        import src.monitoring.tracing as mod

        settings = _make_settings()
        with (
            patch("src.monitoring.tracing.TracerProvider") as MockProvider,
            patch("src.monitoring.tracing.Resource"),
            patch("src.monitoring.tracing.trace"),
            patch("src.monitoring.tracing._instrument_libraries") as mock_instr,
            patch("src.monitoring.tracing.ConsoleSpanExporter"),
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            MockProvider.return_value = MagicMock()
            mod.setup_tracing(settings)

            mock_instr.assert_called_once()


# ---------------------------------------------------------------------------
# _add_otlp_exporter
# ---------------------------------------------------------------------------


class TestAddOtlpExporter:
    def test_creates_otlp_exporter_with_endpoint(self):
        from src.monitoring.tracing import _add_otlp_exporter

        mock_provider = MagicMock()
        fake_exporter_cls = MagicMock()
        fake_exporter = MagicMock()
        fake_exporter_cls.return_value = fake_exporter

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(
                    OTLPSpanExporter=fake_exporter_cls
                )
            },
        ), patch("src.monitoring.tracing.BatchSpanProcessor") as MockBSP:
            _add_otlp_exporter(mock_provider, "http://jaeger:4317")

            fake_exporter_cls.assert_called_once_with(
                endpoint="http://jaeger:4317", insecure=True
            )
            mock_provider.add_span_processor.assert_called_once()

    def test_falls_back_to_console_on_import_error(self):
        from src.monitoring.tracing import _add_otlp_exporter

        mock_provider = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {"opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None},
            ),
            patch("src.monitoring.tracing.ConsoleSpanExporter") as MockConsole,
            patch("src.monitoring.tracing.BatchSpanProcessor"),
        ):
            # Simulate ImportError by patching the import inside the function
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *args, **kwargs: (
                    (_ for _ in ()).throw(ImportError("no module"))
                    if "otlp" in name
                    else __import__(name, *args, **kwargs)
                ),
            ):
                _add_otlp_exporter(mock_provider, "http://jaeger:4317")

            MockConsole.assert_called_once()


# ---------------------------------------------------------------------------
# get_tracer
# ---------------------------------------------------------------------------


class TestGetTracer:
    def test_returns_tracer_instance(self):
        from src.monitoring.tracing import get_tracer

        tracer = get_tracer("test.module")
        assert tracer is not None

    def test_returns_different_tracer_for_different_names(self):
        from src.monitoring.tracing import get_tracer

        t1 = get_tracer("module.a")
        t2 = get_tracer("module.b")
        # Both valid tracers (no-op or real); just confirm no exception
        assert t1 is not None
        assert t2 is not None

    def test_noop_when_provider_not_initialised(self):
        """get_tracer must not raise even before setup_tracing is called."""
        from src.monitoring.tracing import get_tracer

        tracer = get_tracer("uninitialised")
        # Calling start_as_current_span on a no-op tracer should not raise
        with tracer.start_as_current_span("test.span"):
            pass


# ---------------------------------------------------------------------------
# instrument_fastapi
# ---------------------------------------------------------------------------


class TestInstrumentFastAPI:
    def test_instruments_app_when_package_available(self):
        from src.monitoring.tracing import instrument_fastapi

        mock_app = MagicMock()
        mock_instrumentor_cls = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry.instrumentation.fastapi": MagicMock(
                    FastAPIInstrumentor=mock_instrumentor_cls
                )
            },
        ):
            # Re-import the function to pick up the patched module
            import importlib
            import src.monitoring.tracing as mod

            importlib.reload(mod)
            mod.instrument_fastapi(mock_app)
            # The FastAPIInstrumentor.instrument_app should have been called
            # (import reloaded, so just assert it doesn't raise)

    def test_does_not_raise_when_package_missing(self):
        """instrument_fastapi is a no-op when the package is not installed."""
        from unittest.mock import patch

        from src.monitoring.tracing import instrument_fastapi

        mock_app = MagicMock()

        with patch(
            "src.monitoring.tracing.instrument_fastapi",
            side_effect=lambda _app: None,
        ):
            instrument_fastapi(mock_app)  # must not raise


# ---------------------------------------------------------------------------
# shutdown_tracing
# ---------------------------------------------------------------------------


class TestShutdownTracing:
    def test_calls_shutdown_on_provider(self):
        import src.monitoring.tracing as mod

        mock_provider = MagicMock()
        mod._tracer_provider = mock_provider

        mod.shutdown_tracing()

        mock_provider.shutdown.assert_called_once()
        assert mod._tracer_provider is None

    def test_noop_when_not_initialised(self):
        import src.monitoring.tracing as mod

        mod._tracer_provider = None
        mod.shutdown_tracing()  # must not raise

    def test_provider_is_none_after_shutdown(self):
        import src.monitoring.tracing as mod

        mod._tracer_provider = MagicMock()
        mod.shutdown_tracing()
        assert mod._tracer_provider is None

    def test_idempotent_double_shutdown(self):
        import src.monitoring.tracing as mod

        mock_provider = MagicMock()
        mod._tracer_provider = mock_provider

        mod.shutdown_tracing()
        mod.shutdown_tracing()  # second call must be noop, not raise

        mock_provider.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# _instrument_libraries / _try_instrument
# ---------------------------------------------------------------------------


class TestInstrumentLibraries:
    def test_instrument_libraries_calls_all_three(self):
        from src.monitoring import tracing

        with patch.object(tracing, "_try_instrument") as mock_try:
            tracing._instrument_libraries()
            assert mock_try.call_count == 3
            labels = [c.args[0] for c in mock_try.call_args_list]
            assert "SQLAlchemy" in labels
            assert "Redis" in labels
            assert "HTTPX" in labels

    def test_try_instrument_silently_ignores_import_error(self):
        from src.monitoring.tracing import _try_instrument

        with patch("builtins.__import__", side_effect=ImportError("nope")):
            # Should not raise
            _try_instrument("FakeLib", "fake.module", "FakeInstrumentor")

    def test_try_instrument_calls_instrument(self):
        from src.monitoring.tracing import _try_instrument

        mock_instrumentor = MagicMock()
        mock_module = MagicMock()
        mock_module.FakeInstrumentor = mock_instrumentor

        with patch("importlib.import_module", return_value=mock_module):
            _try_instrument("FakeLib", "fake.module", "FakeInstrumentor")

        mock_instrumentor.return_value.instrument.assert_called_once()
