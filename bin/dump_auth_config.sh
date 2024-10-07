#!/bin/bash

# script to dump the current authorization configuration to a .yaml file
# this file can be used as input for the setup-configuration command to load authorizations
# (on different instances)

python src/manage.py dumpdata authorizations autorisaties vng_api_common.jwtsecret \
    --natural-foreign --natural-primary --format=yaml --verbosity 0 --output auth.yaml 2> /dev/null
# It doesn't seem to be possible to directly output the above command to stdout, without
# displaying log messages that would lead to invalid YAML, so instead we output the file
# and then remove it
cat auth.yaml
rm auth.yaml
