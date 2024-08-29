#!/bin/bash

# setup initial configuration using environment variables
# Run this script from the root of the repository

set -e

# wait for required services
${SCRIPTPATH}/wait_for_db.sh

src/manage.py migrate
${SCRIPTPATH}/load_fixtures.sh
src/manage.py setup_configuration --no-selftest
