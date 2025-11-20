#!/bin/bash

set -e

# Set defaults for OTEL
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-openzaak-flower}"

exec celery --app openzaak --workdir src flower
