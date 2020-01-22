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

**Database**

The deployment assumes that a PostgreSQL 11 database cluster is available.

You need:

* credentials for a superuser role (typically `postgres`)
* the host (name) and port of the cluster (e.g. an ip-address and the default
  port `5432`)
* see `vars/db_credentials.example.yml` - save this file as
  `vars/db_credentials.yml` and modify with your own credentials.
* create credentials for Open Zaak database and save them to the file
  `vars/openzaak.yml`. You can use `vars/openzaak.example.yml` as an example.
* create credentials for Open Notificaties database and save them to the file
  `vars/opennotificaties.yml`. You can use `vars/opennotificaties.example.yml`
  as an example.
* if you use NLX save NLX inway key and certificate to the file `vars/nlx.yml`.
  You can use `vars/nlx.example.yml` as an example.

**Persistent storage**

For multi-replica setups and secure file serving, we need a PVC storage class
that supports `ReadWriteMany` - see
[the Kubernetes docs](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes)
for an overview.

On Google Cloud, we can use:

```shell
[user@host]$ gcloud compute disks create --size=10GB --zone=europe-west4-b gce-nfs-disk
```

## Provisioning

The Ansible playbook `provision.yml`:

* sets up the basic cluster requirements, such as the ingress and required
  namespace(s)
* initializes the database: set up the db user, create the application database
  and enable the required database extensions

```shell
[user@host]$ ./deploy.sh provision.yml
```

## Application

Deploy Open Zaak and Open Notificaties:

```shell
[user@host]$ ./deploy.sh apps.yml
```


## Troubleshooting

**Missing `GOOGLE_APPLICATION_CREDENTIALS` error**

If you see:

```
Please set GOOGLE_APPLICATION_CREDENTIALS or explicitly create credentials and
re-run the application.
```

Try to (re-)log in to gcloud:

```shell
[user@host]$ gcloud auth application-default login
```

This should output a new default credentials file, which should be picked up.
