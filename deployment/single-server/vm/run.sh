#!/bin/bash
#
# Run a Debian container to test the deployment against.
#

PUBKEY=${SSH_PUB_KEY:-~/.ssh/id_rsa.pub}

# Copy public key to tempfile to use as authorized_keys for passwordless SSH
cp $PUBKEY /tmp/openzaak-authorized_keys

docker build -t openzaak-vm .

docker volume create openzaak-vm
docker volume create opennotificaties-vm
docker run \
    --rm \
    --name openzaak-vm \
    -p '2222:22' \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /tmp/openzaak-authorized_keys:/root/.ssh/authorized_keys \
    -v openzaak-vm:/home/openzaak \
    -v opennotificaties-vm:/home/opennotificaties \
    openzaak-vm &
