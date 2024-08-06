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

for component in "${COMPONENTS[@]}";
do
    echo "Linting src/openzaak/components/$component/openapi.yaml ..."
    spectral lint "src/openzaak/components/$component/openapi.yaml"
done
