#!/bin/bash
# Deploy an Ansible playbook
#
# Usage: ./deploy.sh playbook.yml [--any-ansible-playbook-arguments]
#
# Requires a virtualenv to be active with the local dependencies, as
# ansible_python_interpreter is derived from that.
#

set -ex

if [[ ! -z "$VIRTUALENV" ]]; then
    echo "activate your virtualenv"
    exit 1
fi

playbook=$1
shift

ansible-playbook $playbook -e "ansible_python_interpreter=$(which python)" "$@"
