#!/bin/bash

# script to dump the current authorization configuration to a .yaml file
# this file can be used as input for the setup-configuration command to load authorizations
# (on different instances)

src/manage.py dumpdata authorizations autorisaties vng_api_common.jwtsecret --natural-foreign --natural-primary --format=yaml > auth.yaml
