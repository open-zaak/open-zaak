#!/bin/bash

# Dump component data
# This script is not intended for a data migration to another Open Zaak instance.
# Run this script from the root of the repository
#
# Note that postgres 17 requires postgres-client-17
#
# By default a schema and data dump are created separately. This can be changed with the flags --data-only, --schema-only
# or --combined which appends the data dump to the schema dump.
# The schema dump could not use -t to filter tables because this excludes extensions like postgis in the dump.
# pg_dump also does not add related tables automatically, so `dump_data.sh zaken` does not add related zaaktype data to the dump.
#
# with --csv a csv dump can be created for all tables in the given components. The csv files will be generated in the temporary directory csv_dumps
# and combined into a single TAR archive csv_dumps.

set -e

DEFAULT_APPS=(besluiten catalogi documenten zaken)

export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}
export PGUSER=${DB_USER:-openzaak}
export PGDATABASE=${DB_NAME:-openzaak}
export PGPASSWORD=${DB_PASSWORD:-""}

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

${SCRIPTPATH}/wait_for_db.sh

DEFAULT_FILE_NAME="dump_$(date +'%Y-%m-%d_%H-%M-%S')"
DUMP_FILE=${DUMP_FILE:-"$DEFAULT_FILE_NAME.sql"}
TAR_FILE=${TAR_FILE:-"$DEFAULT_FILE_NAME.tar"}
CSV_OUTPUT_DIR="csv_dumps"

CSV=false
SCHEMA=true
DATA=true
COMBINED=false

for arg in "$@"; do
    case "$arg" in
    --csv) CSV=true ;;
    --schema-only) DATA=false ;;
    --data-only) SCHEMA=false ;;
    --combined) COMBINED=true ;;
    --*)
        echo "Unknown flag: $arg"
        exit 1
        ;;
    *)
        APPS+=("$arg")
        ;;
    esac
done

# export given apps or export DEFAULT_APPS
if [ "${#APPS[@]}" -eq 0 ]; then
    APPS=("${DEFAULT_APPS[@]}")
fi

echo >&2 "exporting: ${APPS[*]}"

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
    pg_dump "${INCLUDES[@]}" --disable-triggers --data-only >"$1"
}

append_data() {
    echo "Appending data to $1..."
    pg_dump "${INCLUDES[@]}" --disable-triggers --data-only |
        sed '/^SET\|^SELECT pg_catalog.set_config/d' >>"$1"
}

dump_csv() {
    mkdir -p $CSV_OUTPUT_DIR
    echo "Dumping data to csv..."

    WHERE_CLAUSE=""
    for app in "${APPS[@]}"; do
        if [ -n "$WHERE_CLAUSE" ]; then
            WHERE_CLAUSE+=" OR "
        fi
        WHERE_CLAUSE+="tablename LIKE '${app}_%'"
    done

    TABLES=$(psql -Atc "SELECT tablename FROM pg_tables WHERE schemaname='public' AND ($WHERE_CLAUSE);")

    for table in $TABLES; do
        echo "dumping $table..."
        psql -c "\copy $table TO '$CSV_OUTPUT_DIR/$table.csv' WITH CSV HEADER"
    done

    tar -cf "$TAR_FILE" -C "$CSV_OUTPUT_DIR" .
    rm -rf "$CSV_OUTPUT_DIR"
}

if $CSV; then
    dump_csv
    exit 0
fi

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
