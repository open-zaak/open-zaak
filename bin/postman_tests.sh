#!/bin/sh

openzaak_url=localhost:8000
nrc_url=localhost:8001

status=$(curl -s -o /dev/null -w "%{http_code}" $openzaak_url)
until [ "$status" = "200" ]; do
    >&2 echo "Waiting until migrations are finished..."
    sleep 3
    status=$(curl -s -o /dev/null -w "%{http_code}" $openzaak_url)
done

# TODO add url for NRC
# Download and execute the ZGW postman tests
wget https://api-test.nl/api/v1/postman-test/get_version/ZGW_api_postman_tests/1.0.0/ -O tests.json
NODE_OPTIONS="--max-old-space-size=2048" node_modules/newman/bin/newman.js run tests.json \
    --env-var zrc_url=$openzaak_url/zaken/api/v1 \
    --env-var drc_url=$openzaak_url/documenten/api/v1 \
    --env-var ztc_url=$openzaak_url/catalogi/api/v1 \
    --env-var brc_url=$openzaak_url/besluiten/api/v1 \
    --env-var nrc_url=$nrc_url/api/v1 \
    --env-var ac_url=$openzaak_url/authorizations/api/v1 \
    --env-var referentielijst_url=https://referentielijsten-api.vng.cloud/api/v1 \
    --env-var mock_url=https://c9ac80e5-f4f6-46f9-9e64-a164c03b5f25.mock.pstmn.io \
    --env-var client_id=$client_id \
    --env-var secret=$secret \
    --env-var client_id_limited=$client_id_limited \
    --env-var secret_limited=$secret_limited \
    --timeout-request 5000
