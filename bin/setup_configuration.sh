#!/bin/bash

# setup initial configuration using environment variables
# Run this script from the root of the repository

set -e

# wait for required services
${SCRIPTPATH}/wait_for_db.sh

src/manage.py migrate

# Convert to lowercase
auth_config_enable="${AUTHORIZATIONS_CONFIG_ENABLE,,}"
if [ "$auth_config_enable" = "true" ] || [ "$auth_config_enable" = "1" ] || [ "$auth_config_enable" = "yes" ] || \
   [ "$auth_config_enable" = "on" ] || [ "$auth_config_enable" = "y" ]; then
    # Fixtures have to be loaded first if authorizations will be configured with
    # setup_configuration, because this configuration step relies on Catalogi existing
    # in the database
    ${SCRIPTPATH}/load_fixtures.sh
fi

src/manage.py setup_configuration --no-selftest
