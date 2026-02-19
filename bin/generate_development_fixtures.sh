# Dump the DB content in a fixture file
src/manage.py dumpdata \
    --indent 4 \
    --natural-foreign \
    --natural-primary \
    -o "docker/fixtures/catalogi.json" \
    catalogi
