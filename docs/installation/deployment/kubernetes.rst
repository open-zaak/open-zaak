.. _deployment_kubernetes:

=======================
Deploying on Kubernetes
=======================

.. epigraph::

    `Kubernetes`_ is an open-source system for automating deployment,
    scaling, and management of containerized applications.

    -- kubernetes.io


Kubernetes (K8s) is one of the main supported targets for deployment. We
provide a fully automated deployment toolset suitable for DevOps engineers
and/or system administrators.

This documentation will sketch out the architecture, document the initial
requirements and teach you how to deploy on K8s.

This setup is tested against a Google Cloud Kubernetes cluster with 4vCPU and
15G of memory - two ``n2-standard-2`` nodes. See the documentation for the
available `machine types`_. Please see :ref:`installation_hardware` to
determine your hardware requirements.

.. _machine types: https://cloud.google.com/compute/docs/machine-types#n2_standard_machine_types

Assumed/required knowledge level of Kubernetes
==============================================

Kubernetes is a complex infrastructure with a lot of moving parts and a steep
learning curve.

We assume you have some familiarity with the following concepts:

* `Namespaces`_
* `Deployments`_
* `Services`_
* `Ingresses`_
* `Persistent volumes`_

Additionally, familiarity with the `kubectl`_ command line tool is a big
advantage.

You should be able to save a ``kube-config`` file and optionally specify its
location via the ``KUBECONFIG`` environment variable.

.. _Namespaces: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/
.. _Deployments: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
.. _Services: https://kubernetes.io/docs/concepts/services-networking/service/
.. _Ingresses: https://kubernetes.io/docs/concepts/services-networking/ingress/
.. _Persistent volumes: https://kubernetes.io/docs/concepts/storage/persistent-volumes/
.. _kubectl: https://kubernetes.io/docs/reference/kubectl/overview/

Target platform
---------------

This guide is written and tested against a Kubernetes cluster on Google Cloud.

Google cloud resources can be managed with the `gcloud`_ command line tool, or
alternatively in the cloud console via point and click.

We have collected a number of example commands to spin up an environment.

**Creating a cluster**

See the documentation to `create a cluster`_ and the prerequisites. We assume
a Google Cloud project name of ``gemeente``.

.. code-block:: shell

  [user@host]$ gcloud container --project "gemeente" clusters create "test-cluster" \
      --zone "europe-west4-b" \
      --cluster-version "1.14.8-gke.12" \
      --machine-type "n2-standard-2" \
      --num-nodes "2"

**Creating a database**

From the documentation to `create an SQL instance`_:

.. code-block:: shell

  [user@host]$ gcloud sql instances create test \
    --assign-ip \
    --region europe-west4 \
    --zone europe-west4-b \
    --database-version POSTGRES_11 \
    --root-password letmein \
    --cpu 2 \
    --memory 7GiB

In your Google Cloud console you can then configure the remote networks that
are allowed to access this instance. You should at least include the network
from where you are deploying.

Additionally, it's recommended to set up a `private IP`_ so connections from
the Kubernetes cluster are allowed.

.. _gcloud: https://cloud.google.com/sdk/install
.. _create a cluster: https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-cluster
.. _create an SQL instance: https://cloud.google.com/sql/docs/postgres/cloud-sdk
.. _private IP: https://cloud.google.com/sql/docs/postgres/private-ip

Application architecture
========================

Typically, your K8s cluster provider will set up a load balancer in front
of your cluster, directing all the traffic to services in the cluster.

DNS is set up so that your domain name(s) point to the IP address of the load
balancer.

The load balancer will then pass the traffic to an *Ingress* in the cluster,
which will route the traffic to the backend services.

All applications make use of caching via Redis cache databases.

Open Zaak
---------

Traffic from the ingress will enter Open Zaak at one or multiple `NGINX`_
reverse proxies. NGINX will performs one of two possible tasks:

* pass the request to the Open Zaak application or
* send the binary data of uploaded files to the client

NGINX exists to serve uploaded files in a secure and performant way, reducing
load on the Open Zaak application.

All other requests are passed to the Open Zaak application.

Open Notificaties
-----------------

Traffic from the ingress is directly passed to the Open Notificaties
application. Open Notificaties then communicates with async workers (using
RabbitMQ) to distribute the notifications to all the relevant subscribers.

Environment requirements
========================

Before you begin, you will need:

* a kubernetes cluster that you can access, this means you need a valid
  ``~/.kube/config`` file. You can override which kube config to use by setting
  the ``KUBECONFIG`` environment variable if you manage multiple clusters.

  If you are dealing with jump/bastion hosts, complicated firewalls... Please
  contact your provider on how you can access your cluster from your local
  machine.

* a PostgreSQL (10 or 11) database server with credentials:

    * a database hostname that you can reach from your local machine
    * a database hostname that can be reached from your K8s cluster (possibly
      the same as above)
    * the username of a superuser (typically ``postgres``)
    * a password for the superuser
    * credentials for the Open Zaak database and Open Notificaties database

* A persistent-volume storage class supporting ``ReadWriteMany``. Contact your
  provider to see if they offer it. If this is not an option, you can use a
  ``ReadWriteOnce`` storage class and set up an NFS-server around it, but this
  will likely have slower performance.

  On Google Cloud, you can use:

  .. code-block:: shell

      [user@host]$ gcloud compute disks create --size=10GB --zone=europe-west4-b gce-nfs-disk

.. _deployment_kubernetes_tooling:

Deployment requirements
=======================

Fully automated deployment is implemented with `Ansible`_. Ansible runs on your
local machine (control host) and connects to the required services to realize
the desired state.

For example, to create the application database, it will create a database
connection and execute the necessary queries. To manage kubernetes objects,
it will use the Kubernetes API via your ``KUBECONFIG``.

Ansible is a Python tool and has a number of dependencies. The deployment is
tested on Python 3.7.

Get a copy of the deployment configuration
------------------------------------------

You can either clone the https://github.com/open-zaak/open-zaak repository,
or download and extract the latest ZIP:
https://github.com/open-zaak/open-zaak/archive/master.zip

Ensure you have a suitable Python version
-----------------------------------------

Check your operation system packages and make sure you have installed a recent
enough Python version. We recommend using Python 3.7.

Create a virtual environment
----------------------------

Virtual environments isolate dependencies between environments. It gives us
close control over the exact required versions.

Create a virtualenv:

.. code-block:: shell

    [user@host]$ python3.7 -m venv env

This creates a virtualenv named ``env``. Next, activate the virtualenv. You
need to do this every time you want to use the deployment tooling.

.. code-block:: shell

    [user@host]$ source env/bin/activate

Install dependencies
--------------------

First, navigate to the correct directory. In the folder where you placed the
copy of the repository, change into the ``deployment`` directory:

.. code-block:: shell

    (env) [user@host]$ cd /path/to/open-zaak/deployment/

To install the required dependencies, we use the Python package manager ``pip``:

.. note::

    These requirements are different from the the ones in the Open Zaak root
    directory. They can be installed on top of eachother though.

.. code-block:: shell

    (env) [user@host]$ pip install -r requirements.txt
    (env) [user@host]$ cd kubernetes
    (env) [user@host]$ ansible-galaxy collection install -r requirements.yml

Roughly said, this installs Ansible and the modules to talk to the PostgreSQL
database and Kubernetes API.

Deploying (automated or manual)
===============================

Ansible has the concept of *playbooks* - a predefined set of tasks to execute,
logically grouped.

Open Zaak ships with two playbooks:

* ``provision.yml``:

    * finishes the configuration of your Kubernetes cluster (if needed)
    * initializes the application databases

* ``apps.yml``:

    * installs Open Zaak
    * installs Open Notificaties

You can run the Ansible-playbooks as-is (with some configuration through
variables), or use them an inspiration for manual deployment.

Provisioning
------------

Below you find some guidance to modify the provisioning specifically to your
needs.

I already have an ingress-controller
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set the variable ``needs_ingress`` in ``provision.yml`` to ``no``. Otherwise,
Traefik 2.0 is set up as Ingress controller.

I have a ``ReadWriteMany`` storage solution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set the variable ``needs_nfs`` in ``provision.yml`` to ``no``. Otherwise,
a NFS-server is deployed to use as ``ReadWriteMany`` solution.

.. todo:: streamline nfs/RWX solution!

Database configuration
^^^^^^^^^^^^^^^^^^^^^^

The playbook will set up the application database user(s) with the correct,
minimal permissions and will set up the databases for the applications. To be
able to do this, you need superuser access. See the
``vars/db_credentials.example.yml`` file for the example configuration.

Both Open Zaak and Open Notificaties require database configuration to be
defined in the ``vars/open-zaak.yml`` and ``vars/open-notificaties.yml``
variable files:

.. code-block:: yaml

    openzaak_db_name: openzaak  # name of the database to create
    openzaak_db_host: postgres.gemeente.nl  # hostname or IP address of the database server
    openzaak_db_port: "5432"  # database server port, default is 5432
    openzaak_db_username: openzaak  # username of the application database user
    openzaak_db_password: secret  # password of the application database user

For Open Notificaties, the prefix is ``opennotificaties`` instead of ``openzaak``.

Applying the provisioning
^^^^^^^^^^^^^^^^^^^^^^^^^

Run the ``provision.yml`` playbook using:

.. code-block:: shell

    (env) [user@host]$ ./deploy.sh provision.yml


Applications
------------

The ``apps.yml`` playbook sets up the Open Zaak and Open Notificaties
installations.

I already have an ingress-controller
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. todo:: opt-out of the Traefik CRD and provide an alternative Ingress resource

Configuring Open Zaak
^^^^^^^^^^^^^^^^^^^^^

To deploy Open Zaak, some variables need to be set (in ``vars/open-zaak.yml``):

* ``openzaak_domain``: the domain name, e.g. ``open-zaak.gemeente.nl``
* ``openzaak_secret_key``: generate a key via https://miniwebtool.com/django-secret-key-generator/.
  Make sure to put the value between single quotes!

See ``roles/openzaak/defaults/main.yml`` for other possible variables to
override.

Configuring Open Notificaties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To deploy Open Notificaties, some variables need to be set (in ``vars/open-notificaties.yml``):

* ``opennotificaties_domain``: the domain name, e.g. ``open-notificaties.gemeente.nl``
* ``opennotificaties_secret_key``: generate a key via https://miniwebtool.com/django-secret-key-generator/.
  Make sure to put the value between single quotes!

See ``roles/opennotificaties/defaults/main.yml`` for other possible variables to
override.

Configuring NLX
^^^^^^^^^^^^^^^

If you want to use NLX, you need to create NLX certificate. See https://docs.nlx.io/try-nlx/retrieve-a-demo-certificate.
The key and certificate need to be set in ``vars/nlx.yml``:

* ``nlx_inway_key``: private key
* ``nlx_inway_cert``: certificate


Deploying the applications
^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure your ``kubectl`` command can access the correct cluster:

.. code-block:: shell

    (env) [user@host]$ kubectl cluster-info

Run the ``apps.yml`` playbook using:

.. code-block:: shell

    (env) [user@host]$ ./deploy.sh apps.yml

.. _Kubernetes: https://kubernetes.io/
.. _NGINX: https://www.nginx.com/
.. _Ansible: https://www.ansible.com/

Next steps
==========

You may want to :ref:`customize the logging setup<installation_logging_customize>`. The
default setup should be sufficient to get started though.

To be able to work with Open Zaak, a couple of things have to be configured first,
see :ref:`installation_configuration` for more details.

.. _deployment_kubernetes_updating:

Updating an Open Zaak installation
==================================

Make sure you have the deployment tooling installed - see
:ref:`deployment_kubernetes_tooling` for more details.

If you have an existing environment (from the installation), make sure to update it:

.. code-block:: shell

    # fetch the updates from Github
    [user@host]$ git fetch origin

    # checkout the tag of the version you wish to update to, e.g. 1.0.0
    [user@host]$ git checkout X.Y.z

    # activate the virtualenv
    [user@host]$ source env/bin/activate

    # ensure all (correct versions of the) dependencies are installed
    (env) [user@host]$ pip install -r requirements.txt

Open Zaak deployment code defines variables to specify the Docker image tag to use. This
is synchronized with the git tag you're checking out.

.. warning::

    Make sure you are aware of possible breaking changes or manual interventions by
    reading the :ref:`development_changelog`!

Make sure your ``kubectl`` command can access the correct cluster:

.. code-block:: shell

    (env) [user@host]$ kubectl cluster-info

.. note:: 

    You need access to the cluster for ``kubectl`` to work. With Google Cloud 
    you can get the proper configuration using the Google Cloud SDK:

    .. code-block:: shell

        (env) [user@host]$ gcloud container clusters get-credentials <cluster name> --region <region>

    For the proper authentication setup, you might need a service account. See
    the 
    [Getting Started with Authentication on Google Cloud](https://cloud.google.com/docs/authentication/getting-started#command-line).


Next, to perform the upgrade, you run the ``apps.yml`` playbook just like with the
installation:

.. code-block:: shell

    (env) [user@host]$ ./deploy.sh apps.yml

You can see the status and events with:

.. code-block:: shell

    (env) [user@host]$ kubectl -n <namespace> get pods
    (env) [user@host]$ kubectl -n <namespace> describe pod <pod name>

.. note::

    In the Kubernetes deployment setup, Open Zaak makes use of multiple replicas by
    default, and is set up to perform rolling releases. This means that the old version
    stays live until all new versions are running without errors.

    We make use of health checks and liveness probes to achieve this.

    This does mean that there's a brief window where clients may hit the old or new
    version at the same time - usually this shouldn't pose a problem though.
