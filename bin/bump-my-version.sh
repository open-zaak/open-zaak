#!/usr/bin/env bash
#
# Script to bump the version. Arguments are forwarded to bump-my-version.
#
# Usage:
#
#   ./bin/bumpversion.sh bump minor|patch|pre|build
#

set -eu -o pipefail

toplevel=$(git rev-parse --show-toplevel)
cd $toplevel

# Ensure a virtualenv is active.
if [ -z $VIRTUAL_ENV ]; then
    echo "VIRTUAL_ENV envvar is not set, you must activate your virtualenv before running this script."
    exit 1
fi

# Forward all arguments to bump-my-version binary
bump-my-version "$@"

# Run npm install to update the package-lock.json version number
npm i
