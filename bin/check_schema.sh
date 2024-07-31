#!/bin/bash

# Run this script from the root of the repository

set -e

COMPONENTS=(
    autorisaties
    besluiten
    catalogi
    documenten
    zaken
)

if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -v GITHUB_ACTIONS ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

for component in "${COMPONENTS[@]}";
do
    ./bin/generate_schema_for_component.sh "$component" "openapi-$component.yaml"

    echo "Checking src/openzaak/components/$component/openapi.yaml ..."

    diff "openapi-$component.yaml" "src/openzaak/components/$component/openapi.yaml"

    if (( $? > 0 )); then
        echo "src/openzaak/components/$component/openapi.yaml needs to be updated!"
    else
        echo "src/openzaak/components/$component/openapi.yaml is up-to-date."
    fi
done
