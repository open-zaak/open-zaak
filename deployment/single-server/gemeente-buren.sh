#!/bin/bash

ansible-playbook open-zaak.yml \
    -i gemeente-buren-hosts \
    --limit webref01 \
    -e "certbot_create_if_missing=false openzaak_domain=open-zaak.buren.lan openzaak_version=20200108 app_db_name=openzaak-staging app_db_user=openzaak-staging" \
    -c local \
    --become \
    --become-method=sudo \
    --ask-become-pass

