from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)


'''
SETUP
'''
trace.set_tracer_provider(TracerProvider())

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

meter = metrics.get_meter(__name__)

'''
METRICS
'''
request_counter_health_endpoint = meter.create_counter(
    name='django_health_requests_total',
    description='Total HTTP requests',
)
