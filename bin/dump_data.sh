#!/bin/bash

# Dump component data
# Run this script from the root of the repository
# dump_data.sh for all apps or dump_data.sh zaken documenten ... to specify specific apps

set -e

DEFAULT_APPS=(besluiten catalogi documenten zaken)

export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}
export PGUSER=${DB_USER:-postgres}
export PGDATABASE=${DB_NAME:-postgres}
export PGPASSWORD=${DB_PASSWORD:-""}

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

${SCRIPTPATH}/wait_for_db.sh

DUMP_FILE=${DUMP_FILE:-"dump_$(date +'%Y-%m-%d_%H-%M-%S').sql"}

# export given apps or export DEFAULT_APPS
if [ "$#" -gt 0 ]; then
  APPS=("$@")
else
  APPS=("${DEFAULT_APPS[@]}")
fi

>&2 echo "exporting: ${APPS[*]}"

# create -t flags for each app
INCLUDES=()
for app in "${APPS[@]}"; do
    INCLUDES+=("-t" "${app}_*")
done

pg_dump "${INCLUDES[@]}" -f "$DUMP_FILE"

>&2 echo "database was exported to $DUMP_FILE"
