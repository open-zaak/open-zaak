#!/bin/bash
# Liveness probe for OpenZaak Celery workers.
#
# Checks that the worker is actually alive and processing its event loop,
# by using maykin-common command
#

set -e

QUEUE=${CELERY_WORKER_QUEUE:=celery}
WORKER_LIVENESS_FILE=${CELERY_LIVENESS_FILE:-/app/tmp/celery_worker_event_loop.live}
WORKER_MAX_AGE=${CELERY_MAX_AGE:-70}

if [ -z "$CELERY_WORKER_NAME" ]; then
  WORKER_NAME="${QUEUE}@${HOSTNAME}"
else
  if [[ "$CELERY_WORKER_NAME" != *"@"* ]]; then
    WORKER_NAME="celery@${CELERY_WORKER_NAME}"
  else
    WORKER_NAME="${CELERY_WORKER_NAME}"
  fi
fi

maykin-common worker-health-check \
  --broker=${CELERY_BROKER_URL} \
  --worker-name=${WORKER_NAME} \
  --liveness-file=${WORKER_LIVENESS_FILE} \
  --max-age=${WORKER_MAX_AGE}
