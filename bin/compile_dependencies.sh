#!/bin/bash

set -ex

toplevel=$(git rev-parse --show-toplevel)

cd $toplevel

# Base (& prod) deps
pip-compile \
    --no-index \
    requirements/base.in

# Dependencies for testing
pip-compile \
    --no-index \
    --output-file requirements/test.txt \
    requirements/base.txt \
    requirements/testing.in

# Dev depedencies - exact same set as CI + some extra tooling
pip-compile \
    --no-index \
    --output-file requirements/dev.txt \
    requirements/test.txt \
    requirements/dev.in
