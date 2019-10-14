#!/bin/sh

# Download and install ngrok
curl -s https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip > ngrok.zip
unzip ngrok.zip
sudo apt install jq

# Create tunnel to localhost:8000
./ngrok http 8000 > /dev/null &
sleep 2

# Retrieve publicly availabe URL
NGROK_URL=$(curl -s localhost:4040/api/tunnels/command_line | jq --raw-output .public_url)

test_platform_url=https://vng-test.maykin.nl

# TODO build separate nrc
data=$(curl -d \
    "
    {\"test_scenario\": \"ZGW api tests\",\"endpoints\":
        [
            {\"name\": \"zrc_url\", \"value\": \"$NGROK_URL/zaken/api/v1\"},
            {\"name\": \"drc_url\", \"value\": \"$NGROK_URL/documenten/api/v1\"},
            {\"name\": \"ztc_url\", \"value\": \"$NGROK_URL/catalogi/api/v1\"},
            {\"name\": \"brc_url\", \"value\": \"$NGROK_URL/besluiten/api/v1\"},
            {\"name\": \"nrc_url\", \"value\": \"$NGROK_URL/notificaties/api/v1\"},
            {\"name\": \"ac_url\", \"value\": \"$NGROK_URL/autorisaties/api/v1\"},
            {\"name\": \"referentielijst_url\", \"value\": \"https://referentielijsten-api.vng.cloud/api/v1\"},
            {\"name\": \"mock_url\", \"value\": \"https://c9ac80e5-f4f6-46f9-9e64-a164c03b5f25.mock.pstmn.io\"},
            {\"name\": \"client_id\", \"value\": \"$client_id\"},
            {\"name\": \"secret\", \"value\": \"$secret\"},
            {\"name\": \"client_id_limited\", \"value\": \"$client_id_limited\"},
            {\"name\": \"secret_limited\", \"value\": \"$secret_limited\"}
        ]
    }" \
    --header "Authorization: Token $apt_token" -H "Content-Type: application/json" \
    -X POST $test_platform_url/api/v1/provider-run/ -w "\n")

echo Response from API test platform $data

id=$(echo $data | jq '.id' -r)
uuid=$(echo $data | jq '.uuid' -r)

status="Running"
until [ "$status" = "Completed" ]; do
  >&2 echo "Waiting until provider test is finished..."
  sleep 5
  status=$(curl --header "Authorization: Token $apt_token" $test_platform_url/api/v1/provider-run/$id -w "\n" -L | jq '.status_exec' -r)
done

shield=$(curl --header "Authorization: Token $apt_token" $test_platform_url/api/v1/provider-run-shield/$uuid -L -w "\n")

message=$(echo $shield | jq '.message' -r)

echo Result is: $message

if [ $message = "Success" ];
then
    exit 0
else
    exit 1
fi
