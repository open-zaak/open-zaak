#!/bin/bash

set -e  # exit on errors
set -x  # echo commands

if [[ -z "$WORKSPACE" ]]; then
    export WORKSPACE=$(pwd)
fi

# use the Jenkins specific override
cp bin/docker-compose.override.yml docker-compose.override.yml

docker-compose build tests
docker-compose run tests

# cleanup
git reset --hard
