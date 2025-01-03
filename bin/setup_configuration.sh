#!/bin/bash

# setup initial configuration using an yaml file
# Run this script from the root of the repository

set -e

if [[ "${RUN_SETUP_CONFIG,,}" =~ ^(true|1|yes)$ ]]; then
    # wait for required services
    /wait_for_db.sh

    src/manage.py migrate
    src/manage.py setup_configuration --yaml-file setup_configuration/data.yaml
fi
