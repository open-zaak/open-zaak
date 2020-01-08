#!/bin/bash

ansible-playbook open-zaak.yml \
    -i gemeente-buren-hosts \
    -e "certbot_create_if_missing=false openzaak_version=20200108" \
    -c local \
    --become \
    --become-method=sudo \
    --ask-vault-pass

