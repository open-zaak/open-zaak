#!/bin/sh

set -x

# These client IDs and secrets are dummy variables that are only used by
# the Docker build in Travis, so they can be public
client_id=zgw_api_tests
secret=secret
client_id_limited=zgw_api_tests_limited
secret_limited=secret_limited

openzaak_url=localhost:8000
nrc_url=localhost:8001

status=$(curl -s -o /dev/null -w "%{http_code}" $openzaak_url)
until [ "$status" = "200" ]; do
    >&2 echo "Waiting until migrations are finished..."
    sleep 3
    status=$(curl -s -o /dev/null -w "%{http_code}" $openzaak_url)
    docker ps
done

status=$(curl -s -o /dev/null -w "%{http_code}" $nrc_url)
until [ "$status" = "200" ]; do
    >&2 echo "Waiting until notification migrations are finished..."
    sleep 3
    status=$(curl -s -o /dev/null -w "%{http_code}" $nrc_url)
    docker ps
done

# Download and execute the ZGW postman tests
wget https://api-test.nl/api/v1/postman-test/get_version/ZGW_api_postman_tests/1.0.0 -O tests.json

# Run the tests using the newman library for nodejs
node bin/newman_tests.js \
    --zrc_url=$openzaak_url/zaken/api/v1 \
    --drc_url=$openzaak_url/documenten/api/v1 \
    --ztc_url=$openzaak_url/catalogi/api/v1 \
    --brc_url=$openzaak_url/besluiten/api/v1 \
    --nrc_url=$nrc_url/api/v1 \
    --ac_url=$openzaak_url/autorisaties/api/v1 \
    --referentielijst_url=https://referentielijsten-api.vng.cloud/api/v1 \
    --mock_url=http://mock-endpoints.local \
    --client_id=$client_id \
    --secret=$secret \
    --client_id_limited=$client_id_limited \
    --secret_limited=$secret_limited
