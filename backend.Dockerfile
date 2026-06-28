# https://www.docker.com/blog/how-to-dockerize-django-app/
# Use the official Python runtime image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app
 
# Set environment variables 
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1 
 
# Upgrade pip
RUN pip install --upgrade pip 
 
# Copy the Django project  and install dependencies
COPY requirements.txt  /app/
 
# run this command to install all dependencies 
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-instrumentation-django \
  opentelemetry-exporter-otlp \
  opentelemetry-distro

RUN opentelemetry-bootstrap -a install
 
RUN useradd -m -r appuser && \
    chown -R appuser /app

# Copy the Django project to the container
COPY --chown=appuser:appuser . /app/

RUN rm -rf ./.alertmanager \
    && rm -rf ./.alloy \
    && rm -rf ./.ansible \
    && rm -rf ./.clamav \
    && rm -rf ./.dast \
    && rm -rf ./.grafana \
    && rm -rf ./.jenkins-data \
    && rm -rf ./.loki \
    && rm -rf ./.opentelemetry \
    && rm -rf ./.prometheus \
    && rm -rf ./.redis \
    && rm -rf ./.tempo \
    && rm -rf ./.vulnerabilities

RUN rm -rf ./logging/* || mkdir ./logging
RUN touch ./logging/debug.log || true

RUN mkdir ./media || true
RUN mkdir ./static || true
RUN mkdir ./staticfiles || true

ENV OTEL_SERVICE_NAME=website-django
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4320
ENV OTEL_EXPORTER_OTLP_PROTOCOL=grpc
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=website.settings

# Sanity check
RUN python manage.py check
RUN python manage.py check --deploy

# Switch to non-root user
USER appuser

# Expose the Django port
EXPOSE 8000 8888

# Run Django’s development server with auto-telemetry
# CMD ["opentelemetry-instrument", "python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
CMD ["opentelemetry-instrument", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "website.wsgi:application"]
