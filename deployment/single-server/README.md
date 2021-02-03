# Single-server deployment

The [official documentation][docs] documents the installation procedure of Open Zaak. If you're looking
to install Open Zaak, please follow that documentation.

## For maintainers, power-users and devops engineers

This directory contains example [Ansible][Ansible] playbooks to deploy Open Zaak and
(optionally) [NLX][NLX].

The playbooks are built around roles published on [Ansible Galaxy][Galaxy] by the
community. This is also were we published the [Open Zaak Collection][collection],
which provides Open Zaak-specific roles.

## Requirements

* A server with a supported Linux distribution (see the Ansible Collection docs for
  supported distros).
* Root access to the server
* SSH access (with the root user)
* A python virtualenv with the [requirements](../requirements.txt) installed

## Testserver

You can spin up a Debian 'VM' if you don't have a VPS/DDS (yet) to test the
deployment procedure. See the [VM Readme](./vm/README.md).

## Deployment

Follow the guide in the [official documentation][docs] - the steps still apply.


[docs]: https://open-zaak.readthedocs.io/en/stable/installation/deployment/single_server.html
[NLX]: https://nlx.io
[Ansible]: https://www.ansible.com/
[Galaxy]: https://galaxy.ansible.com/
[collection]: https://github.com/open-zaak/ansible-collection
