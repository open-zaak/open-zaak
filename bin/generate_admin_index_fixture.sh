#!/bin/bash
src/manage.py dumpdata --indent=4 --natural-foreign --natural-primary admin_index.AppGroup admin_index.AppLink > src/openzaak/fixtures/default_admin_index.json
