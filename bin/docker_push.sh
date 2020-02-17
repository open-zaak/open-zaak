#!/bin/bash
#
# Build and push the docker image to Docker Hub.
#
# Usage: ./bin/docker_push.sh [image_tag]
#

# error on unset variables, exit on error
set -eu
set +x

git_hash=${TRAVIS_COMMIT:-`git rev-parse HEAD`}

# Login to Docker Hub
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Echo script commands
set -x

REPO=openzaak/open-zaak
TAG=${1:-latest}

# Build the image
docker build \
    -t $REPO:$TAG \
    --build-arg COMMIT_HASH=$git_hash \
    --build-arg RELEASE=$TAG \
    .

# Push the image
docker push $REPO:$TAG
