#!/bin/bash

# Dump component data
# Run this script from the root of the repository
# dump_data.sh for all apps or dump_data.sh zaken documenten ... to specify specific apps
# Note that postgres 17 requires postgres-client-17
#
# By default a schema and data dump are created separately. This can be changed with the flags --data-only, --schema-only
# or --combined which appends the data dump to the schema dump.
# The schema dump could not use -t to filter tables because this excludes extensions like postgis in the dump.
# pg_dump also does not add related tables automatically, so `dump_data.sh zaken` does not add related zaaktype data to the dump.


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

SCHEMA=true
DATA=true
COMBINED=false

for arg in "$@"; do
  case "$arg" in
    --schema-only) DATA=false ;;
    --data-only)   SCHEMA=false ;;
    --combined)    COMBINED=true ;;
    --*)
      echo "Unknown flag: $arg"
      exit 1
      ;;
    *)
      APPS+=("$arg") ;;
  esac
done

# export given apps or export DEFAULT_APPS
if [ "${#APPS[@]}" -eq 0 ]; then
  APPS=("${DEFAULT_APPS[@]}")
fi

>&2 echo "exporting: ${APPS[*]}"

# create -t flags for each app
INCLUDES=()
for app in "${APPS[@]}"; do
    INCLUDES+=("-t" "${app}_*")
done

dump_schema() {
  echo "Dumping schema to $1..."
  pg_dump --schema-only -f "$1"
}

dump_data() {
  echo "Dumping data to $1..."
  pg_dump "${INCLUDES[@]}" --disable-triggers --data-only > "$1"
}

append_data() {
  echo "Appending data to $1..."
  pg_dump "${INCLUDES[@]}" --disable-triggers --data-only \
    | sed '/^SET\|^SELECT pg_catalog.set_config/d' >> "$1"
}


if $COMBINED; then
  dump_schema "$DUMP_FILE"
  append_data "$DUMP_FILE"
  exit 0
fi

if $SCHEMA; then
  dump_schema "schema__$DUMP_FILE"
fi

if $DATA; then
  dump_data "data__$DUMP_FILE"
fi
