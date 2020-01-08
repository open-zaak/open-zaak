#!/bin/bash

ansible-playbook open-notificaties.yml \
    -i gemeente-buren-hosts \
    --limit webref01-notificaties \
    -e "certbot_create_if_missing=false opennotificaties_version=latest app_db_name=opennotificaties-staging app_db_user=opennotificaties-staging" \
    -c local \
    --become \
    --become-method=sudo \
    --ask-become-pass

