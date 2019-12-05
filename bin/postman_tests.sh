#!/bin/sh

set -x

openzaak_url=localhost:8000
nrc_url=localhost:8001

status=$(curl -s -o /dev/null -w "%{http_code}" $openzaak_url)
until [ "$status" = "200" ]; do
    >&2 echo "Waiting until migrations are finished..."
    sleep 3
    status=$(curl -s -o /dev/null -w "%{http_code}" $openzaak_url)
done

status=$(curl -s -o /dev/null -w "%{http_code}" $nrc_url)
until [ "$status" = "200" ]; do
    >&2 echo "Waiting until notification migrations are finished..."
    sleep 3
    status=$(curl -s -o /dev/null -w "%{http_code}" $nrc_url)
done

# Download and execute the ZGW postman tests
wget https://api-test.nl/api/v1/postman-test/get_version/ZGW_api_postman_tests/1.0.0/ -O tests.json

# Run the tests using the newman library for nodejs
node bin/newman_tests.js \
    --zrc_url=$openzaak_url/zaken/api/v1 \
    --drc_url=$openzaak_url/documenten/api/v1 \
    --ztc_url=$openzaak_url/catalogi/api/v1 \
    --brc_url=$openzaak_url/besluiten/api/v1 \
    --nrc_url=$nrc_url/api/v1 \
    --ac_url=$openzaak_url/autorisaties/api/v1 \
    --referentielijst_url=https://referentielijsten-api.vng.cloud/api/v1 \
    --mock_url=https://c9ac80e5-f4f6-46f9-9e64-a164c03b5f25.mock.pstmn.io \
    --client_id=$client_id \
    --secret=$secret \
    --client_id_limited=$client_id_limited \
    --secret_limited=$secret_limited
