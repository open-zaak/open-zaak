#!/bin/bash

ansible-playbook open-zaak.yml \
    -i gemeente-buren-hosts \
    -e "certbot_create_if_missing=false openzaak_version=20200108"
