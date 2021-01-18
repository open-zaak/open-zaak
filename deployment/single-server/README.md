# Single-server deployment

This directory contains the tooling to deploy Open Zaak against a single
server. It has been tested with Debian 9 and 10.

The application is deployed as docker containers, and the playbook will
set up all the required dependencies.

## Requirements

* Debian 9/10 server with root access (see [testserver](#testserver))
* SSH access (with the root user)
* A python virtualenv with the [requirements](../requirements.txt) installed
* Ansible-vault password to decrypt `vars/secrets.yml`

## Testserver

You can spin up a Debian 'VM' if you don't have a VPS/DDS (yet) to test the
deployment procedure. See the [VM Readme](./vm/README.md)

## Deploying
Add secrets to the `vars/secrets.yml` encrypted with Ansible-vault.
You can use `vars/secrets.yml.example` as an example of the content.

```shell
[user@host]$ ansible-vault create vars/secrets.yml
```

Install Ansible requirements:

```shell
[user@host]$ ansible-galaxy role install -r requirements.yml
[user@host]$ ansible-galaxy collection install -r requirements.yml
```

Run the Ansible playbook:

```shell
[user@host]$ ansible-playbook open-zaak.yml --ask-vault-pass
```
