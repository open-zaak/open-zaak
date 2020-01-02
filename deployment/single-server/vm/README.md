# VM-like environment for playbook testing

## What is this?

This directory spins up a Debian server with an SSH daemon to test Ansible
playbooks against. It sets up passwordless SSH and is Docker based. The host
docker socket is mounted into the Debian container so that you can run Docker
containers from the Debian container (as siblings on the host system).

## Run the "VM"

The `run.sh` script will build the image and run it, cleaning up after itself
on exit. It starts the SSH daemon, which can be accessed on the host system on
port 2222, with the root user.

```shell
$ ./run.sh
```

## Running the playbook

The Debian environment slightly differs from a real VPS/DDS because it's not
started with systemd. Therefore we need to override some small configuration
variables.

```shell
$ ansible-playbook open-zaak.yml -i vm/hosts -e "postgresql_daemon=postgresql docker_restart_handler_state=started certbot_create_if_missing=false openzaak_env_file=/var/lib/docker/volumes/openzaak-vm/_data/.env"
```
