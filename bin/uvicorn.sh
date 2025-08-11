cd src/
exec uvicorn openzaak.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --lifespan off \
    --forwarded-allow-ips "*" \
    --proxy-headers