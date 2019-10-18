# Deployment instructions - how to use this

The deployment instructions for Kubernetes are documented here. Extended
documentation is/will be available on
[ReadTheDocs](https://open-zaak.readthedocs.io/).

## Prerequisites

**Deployment tooling**

Ensure you have the necessary deployment tooling installed. We recommend using
a Python 3.7+ virtualenv, and then:

```shell
[user@host]$ pip install -r requirements.txt
```

**Ensure you have a `kube.config`**

You need to have a valid, functioning `kube.config` file with cluster admin
permissions. Consult your (cloud) provider documentation/support on how to
obtain this.

**Test that it's working**

If you have `kubectl`, run:

```shell
[user@host]$ kubectl cluster-info
```

This can be used to verified that your credentials are indeed set up to point
to the correct cluster.


## Provisioning

The Ansible playbook `provision.yml` sets up the basic cluster requirements,
such as the ingress and required namespace(s):

```shell
[user@host]$ ansible-playbook provision.yml
```

## Application

Deploy Open Zaak and Open Notificaties:

```shell
[user@host]$ ansible-playbook apps.yml
```
