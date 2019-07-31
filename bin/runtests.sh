#!/bin/sh

set -e
set -x

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
db_host=${DB_HOST:-db}
db_user=${DB_USER:-postgres}
db_password=${DB_PASSWORD}

until PGPASSWORD=$db_password psql -h "$db_host" -U "$db_user" -c '\q'; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

python src/manage.py jenkins \
  --noinput \
  --project-apps-tests \
  --enable-coverage \
  --coverage-rcfile=setup.cfg

# patch the report so that Jenkins can read the source code for coverage
bad_line="<source>/app/src</source>"
correct_line="<source>${WORKSPACE}/src</source>"
sed -i "s:$bad_line:$correct_line:g" reports/coverage.xml
