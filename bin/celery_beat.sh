#!/bin/bash

set -euo pipefail

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

# Figure out abspath of this script
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

# wait for required services
${SCRIPTPATH}/wait_for_db.sh


echo "Starting celery beat service"
exec celery --app openzaak --workdir src beat --loglevel $LOGLEVEL
