#!/bin/bash

# Dump component data
# Run this script from the root of the repository
# dump_data.sh for all apps or dump_data.sh zaken documenten ... to specify specific apps
# Note that postgres 17 requires postgres-client-17
#
# This script dumps the whole db schema and adds appends the datadump with specified tables.
# The schema dump cannot use -t to filter tables because this excludes extensions like postgis in the dump.
# pg_dump also does not add related tables automatically, so `dump_data.sh zaken` does not add related zaaktype data to the dump.


set -e

DEFAULT_APPS=(besluiten catalogi documenten zaken) # zgw_consumers simple_certmanager

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

# dump full schema
pg_dump --schema-only -f "$DUMP_FILE"

# dump data of tables added to INCLUDES
pg_dump "${INCLUDES[@]}" --disable-triggers --data-only | sed '/^SET\|^SELECT pg_catalog.set_config/d' >> "$DUMP_FILE"

>&2 echo "database was exported to $DUMP_FILE"
