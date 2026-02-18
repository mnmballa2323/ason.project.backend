"""
Telemetry Service — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Configures OpenTelemetry SDK for distributed tracing.
Ensures all traces are sent to the local Jaeger instance (Air-Gapped).
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

def setup_telemetry(service_name: str = "ason-backend"):
    """
    Initialize OpenTelemetry TracerProvider.
    Exports to Jaeger via OTLP (gRPC) and Console (for debug).
    """
    resource = Resource(attributes={
        "service.name": service_name,
        "deployment.environment": "air-gapped-production",
        "cloud.provider": "multi-cloud-mesh"
    })

    provider = TracerProvider(resource=resource)
    
    # 1. OTLP Exporter (Jaeger)
    # Assumes Jaeger is running locally or in the cluster
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # 2. Console Exporter (Optional - for immediate feedback in logs)
    # console_exporter = ConsoleSpanExporter()
    # provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(service_name)

# Singleton tracer
tracer = setup_telemetry()
