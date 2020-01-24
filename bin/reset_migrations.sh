#!/bin/bash
#
# Resets the migrations. Run from the root of the project.
#

WORKDIR=src/openzaak

migration_dirs=$(find $WORKDIR -type d -name migrations)

for dir in $migration_dirs; do
    app_label=$(basename $(dirname $dir))
    src/manage.py migrate $app_label zero --fake
done

src/manage.py migrate notifications_log zero --fake

# fake migrations forwards
src/manage.py migrate --fake
