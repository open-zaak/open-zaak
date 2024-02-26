#!/bin/bash

# setup initial configuration using environment variables
# Run this script from the root of the repository

set -e

src/manage.py setup_configuration --no-selftest
