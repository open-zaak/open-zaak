#!/bin/bash

set -e

exec celery --app openzaak --workdir src flower
