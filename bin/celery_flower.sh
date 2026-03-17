#!/bin/bash

set -e

# Set defaults for OTEL
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-openzaak-flower}"

# 100x less than the defaults
export FLOWER_MAX_TASKS="${FLOWER_MAX_TASKS:-1000}"
export FLOWER_MAX_WORKERS="${FLOWER_MAX_WORKERS:-50}"

# TODO: rename CELERY_RESULT_BACKEND to CELERY_BROKER_URL
BROKER_URL="${CELERY_BROKER_URL:-${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}}"

exec celery \
    --broker "${BROKER_URL}" \
    flower