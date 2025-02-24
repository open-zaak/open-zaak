#!/bin/sh

set -ex

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}

uwsgi_port=${UWSGI_PORT:-8000}
uwsgi_processes=${UWSGI_PROCESSES:-2}
uwsgi_threads=${UWSGI_THREADS:-2}

mountpoint=${SUBPATH:-/}

# Make sure system checks are run
python src/manage.py check

# wait for required services
${SCRIPTPATH}/wait_for_db.sh

# Apply database migrations
>&2 echo "Apply database migrations"
python src/manage.py migrate

${SCRIPTPATH}/load_fixtures.sh

# Create superuser
# specify password by setting DJANGO_SUPERUSER_PASSWORD in the env
# specify username by setting OPENZAAK_SUPERUSER_USERNAME in the env
# specify email by setting OPENZAAK_SUPERUSER_EMAIL in the env
if [ -n "${OPENZAAK_SUPERUSER_USERNAME}" ]; then
    python src/manage.py createinitialsuperuser \
        --no-input \
        --username "${OPENZAAK_SUPERUSER_USERNAME}" \
        --email "${OPENZAAK_SUPERUSER_EMAIL:-admin\@admin.org}"
    unset OPENZAAK_SUPERUSER_USERNAME OPENZAAK_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD
fi

# Start server
>&2 echo "Starting server"
exec uwsgi \
    --http :$uwsgi_port \
    --http-keepalive \
    --manage-script-name \
    --mount $mountpoint=openzaak.wsgi:application \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --enable-threads \
    --processes $uwsgi_processes \
    --threads $uwsgi_threads \
    --buffer-size=65535
