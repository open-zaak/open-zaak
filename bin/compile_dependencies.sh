#!/bin/bash

set -ex

toplevel=$(git rev-parse --show-toplevel)

cd $toplevel

# Base deps
pip-compile \
    --no-index \
    requirements/base.in
