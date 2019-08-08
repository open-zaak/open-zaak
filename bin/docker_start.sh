#!/bin/sh

set -ex

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
db_host=${DB_HOST:-db}
db_user=${DB_USER:-postgres}
db_password=${DB_PASSWORD}
db_port=${DB_PORT:-5432}

fixtures_dir=${FIXTURES_DIR:-/app/fixtures}

uwsgi_port=${UWSGI_PORT:-8000}

until PGPORT=$db_port PGPASSWORD=$db_password psql -h "$db_host" -U "$db_user" -c '\q'; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

>&2 echo "Database is up."

# Apply database migrations
>&2 echo "Apply database migrations"
python src/manage.py migrate

# Load any JSON fixtures present
if [ -d $fixtures_dir ]; then
    echo "Loading fixtures from $fixtures_dir"

    for fixture in $(ls "$fixtures_dir/"*.json)
    do
        echo "Loading fixture $fixture"
        python src/manage.py loaddata $fixture
    done
fi

# Start server
>&2 echo "Starting server"
uwsgi \
    --http :$uwsgi_port \
    --module zrc.wsgi \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --processes 2 \
    --threads 2 \
    --buffer-size=32768
    # processes & threads are needed for concurrency without nginx sitting inbetween
