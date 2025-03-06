#!/bin/bash

# Run this script from the root of the repository

set -e

if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -v GITHUB_ACTIONS ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

if [ "$1" = "" ]; then
    echo "You need to pass the component name in the first argument"
    exit 1
fi

export SUBPATH=/$1/api
export SCHEMA_PATH=src/openzaak/components/$1

OUTPUT_FILE=$2

echo "Generating OAS schema for $1..."
src/manage.py spectacular_for_component \
    --file ${OUTPUT_FILE:-$SCHEMA_PATH/openapi.yaml} \
    --lang="nl" \
    --validate \
    --component $1

echo "Done."
