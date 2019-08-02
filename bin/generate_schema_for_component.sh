#!/bin/bash

# Run this script from the root of the repository

set -e

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

if [ "$1" = "" ]; then
    echo "You need to pass the component name in the first argument"
    exit 1
fi

export SUBPATH=/$1/api

echo "Generating Swagger schema"
src/manage.py generate_swagger_component \
    --overwrite \
    --format=json \
    --mock-request \
    --url https://example.com/api/v1 \
    --component=$1

#echo "Converting Swagger to OpenAPI 3.0..."
#npm run convert
#patch_content_types

echo "Generating resources document"
src/manage.py generate_swagger_component \
    --overwrite \
    --mock-request \
    --url https://example.com/api/v1 \
    --to-markdown-table \
    --component=$1
