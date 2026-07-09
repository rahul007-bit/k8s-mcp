import os
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from traceloop.sdk import Traceloop

def setup_tracing(app_name="k8s-mcp-client"):
    endpoint = os.getenv("OTLP_ENDPOINT", "http://oneuptime.localtest.me/otlp")
    headers = {"x-oneuptime-token": os.getenv("OTLP_TOKEN", "8fff2447-e23b-4890-b7dd-464aaa6e64a0")}

    trace_exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        headers=headers,
    )
    
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{endpoint}/v1/metrics",
        headers=headers,
    )
    
    log_exporter = OTLPLogExporter(
        endpoint=f"{endpoint}/v1/logs",
        headers=headers,
    )

    try:
        Traceloop.init(
            app_name=app_name,
            exporter=trace_exporter,
            metrics_exporter=metric_exporter,
            logging_exporter=log_exporter
        )
    except Exception as e:
        print(f"\n[Warning] Could not initialize OpenTelemetry Traceloop SDK: {e}")
