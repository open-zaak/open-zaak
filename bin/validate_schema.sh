#!/bin/bash

set -ex

docker pull usabillabv/openapi3-validator

docker run --rm \
    -v $(pwd):/project \
    -w /project \
    usabillabv/openapi3-validator \
    src/openapi.yaml
