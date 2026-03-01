"""
OpenTelemetry helpers for farsight_orchestrator.

Defensive behavior:
- If OTel packages are missing, instrumentation is a no-op.
- If OTel is disabled, instrumentation is a no-op.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager
from functools import wraps
from time import perf_counter
from typing import Any, Callable

_OTEL_ENABLED = os.getenv("FARSIGHT_OTEL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
_SETUP_DONE = False
_SETUP_SUCCESS = False

_M_TOOL_CALLS = None
_M_TOOL_ERRORS = None
_M_TOOL_LATENCY_MS = None
_M_ARTIFACT_SAVES = None


def setup_otel() -> bool:
    """
    Initialize tracer/meter providers once.

    Env knobs:
    - FARSIGHT_OTEL_ENABLED=true|false
    - OTEL_SERVICE_NAME (default: farsight-orchestrator)
    - OTEL_EXPORTER_OTLP_ENDPOINT (if unset, use console exporters)
    """
    global _SETUP_DONE, _SETUP_SUCCESS
    global _M_TOOL_CALLS, _M_TOOL_ERRORS, _M_TOOL_LATENCY_MS, _M_ARTIFACT_SAVES

    if _SETUP_DONE:
        return _SETUP_SUCCESS
    _SETUP_DONE = True

    if not _OTEL_ENABLED:
        return False

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except Exception:
        return False

    service_name = os.getenv("OTEL_SERVICE_NAME", "farsight-orchestrator")
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "agent_sandbox",
            "service.version": "0.1.0",
        }
    )

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    tracer_provider = TracerProvider(resource=resource)
    if endpoint:
        span_exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
    else:
        span_exporter = ConsoleSpanExporter()
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    if endpoint:
        metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
    else:
        metric_exporter = ConsoleMetricExporter()
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter("farsight_orchestrator.observability")
    _M_TOOL_CALLS = meter.create_counter(
        "farsight_tool_calls_total",
        unit="1",
        description="Total farsight tool calls",
    )
    _M_TOOL_ERRORS = meter.create_counter(
        "farsight_tool_errors_total",
        unit="1",
        description="Total farsight tool call errors",
    )
    _M_TOOL_LATENCY_MS = meter.create_histogram(
        "farsight_tool_latency_ms",
        unit="ms",
        description="Latency of farsight tool calls in milliseconds",
    )
    _M_ARTIFACT_SAVES = meter.create_counter(
        "farsight_artifact_saves_total",
        unit="1",
        description="Total artifact/report saves by farsight workflow",
    )

    _SETUP_SUCCESS = True
    return True


def _tracer():
    from opentelemetry import trace

    return trace.get_tracer("farsight_orchestrator")


@contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None):
    enabled = setup_otel()
    if not enabled:
        yield None
        return

    with _tracer().start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                if value is None:
                    continue
                span.set_attribute(key, value)
        yield span


def _record_tool_metrics(tool_name: str, status: str, duration_ms: float):
    if not setup_otel():
        return

    attrs = {"tool.name": tool_name, "tool.status": status}
    _M_TOOL_CALLS.add(1, attrs)
    if status != "ok":
        _M_TOOL_ERRORS.add(1, attrs)
    _M_TOOL_LATENCY_MS.record(duration_ms, attrs)


def record_artifact_save(kind: str, status: str):
    if not setup_otel():
        return
    _M_ARTIFACT_SAVES.add(1, {"artifact.kind": kind, "artifact.status": status})


def traced_tool(tool_name: str):
    """Decorator for sync and async tool functions."""

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = perf_counter()
                status = "ok"
                attrs = {
                    "tool.name": tool_name,
                    "ticker": kwargs.get("ticker"),
                    "topic": kwargs.get("topic"),
                }
                with start_span(f"tool.{tool_name}", attrs):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        status = "error"
                        with start_span("tool.error", {"tool.name": tool_name, "error.type": exc.__class__.__name__}):
                            pass
                        raise
                    finally:
                        elapsed_ms = (perf_counter() - start) * 1000.0
                        _record_tool_metrics(tool_name, status, elapsed_ms)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = perf_counter()
            status = "ok"
            attrs = {
                "tool.name": tool_name,
                "ticker": kwargs.get("ticker"),
                "topic": kwargs.get("topic"),
            }
            with start_span(f"tool.{tool_name}", attrs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    status = "error"
                    with start_span("tool.error", {"tool.name": tool_name, "error.type": exc.__class__.__name__}):
                        pass
                    raise
                finally:
                    elapsed_ms = (perf_counter() - start) * 1000.0
                    _record_tool_metrics(tool_name, status, elapsed_ms)

        return sync_wrapper

    return decorator
