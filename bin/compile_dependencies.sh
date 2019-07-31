#!/bin/bash

set -ex

toplevel=$(git rev-parse --show-toplevel)

cd $toplevel

# Base deps
pip-compile \
    --no-index \
    requirements/base.in

# Dev deps
pip-compile \
    --no-index \
    --output-file requirements/dev.txt \
    requirements/base.txt \
    requirements/testing.in \
    requirements/dev.in


# Jenkins/tests deps
pip-compile \
    --no-index \
    --output-file requirements/jenkins.txt \
    requirements/base.txt \
    requirements/dev.txt \
    requirements/jenkins.in
