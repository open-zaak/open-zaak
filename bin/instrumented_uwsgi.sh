#!/bin/sh
#
# Run uwsgi + Open Zaak in profiling mode.
#
# Run from the root of the repository:
#
#   ./bin/profile.sh
# 

set -ex

: ${DB_HOST:=localhost}
: ${DB_PORT:=5432}
: ${DB_NAME:=openzaak-perf}

: ${UWSGI_PROCESSES:=4}
: ${UWSGI_THREADS:=4}
: ${UWSGI_MASTER:=1}

# Fixed settings to enable profiling with Silk & get all the necessary instrumentation.
export \
    DEBUG=false \
    DJANGO_SETTINGS_MODULE=openzaak.conf.dev \
    PROFILE=true \
    ALLOWED_HOSTS=localhost:8000,localhost \
    DB_HOST \
    DB_PORT \
    DB_NAME \
    UWSGI_PROCESSES \
    UWSGI_THREADS \
    UWSGI_MASTER

# Start server
>&2 echo "Starting server"
exec uwsgi \
    --http :8000 \
    --http-keepalive \
    --manage-script-name \
    --mount /=openzaak.wsgi:application \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --enable-threads \
    --buffer-size=65535
