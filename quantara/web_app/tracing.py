import os
import logging

logger = logging.getLogger(__name__)

_has_otel = False
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    _has_otel = True
except ImportError:
    pass


def setup_tracing(app_version: str = "0.1.0"):
    if not _has_otel:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    resource = Resource.create({
        SERVICE_NAME: "quantara-api",
        SERVICE_VERSION: app_version,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    logger.info("OTel tracing enabled, endpoint=%s", endpoint)
