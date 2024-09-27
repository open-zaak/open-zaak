.. _installation_kubernetes:

=====================
Install on Kubernetes
=====================

Open Zaak supports deploying on Kubernetes (K8s) as a first-class citizen, embracing the
`Cloud Native`_ principles.

.. note::

   This section assumes you are familiar with `Kubernetes`_. If this is not the case,
   we advise you to read up on K8s first and come back to this documentation later.

This documentation is aimed at DevOps engineers.

**Quick navigation**

* :ref:`installation_kubernetes_helm`
* :ref:`installation_kubernetes_ansible`

**Requirements**

We recommend deploying on `Haven`_-compliant clusters. The Open Zaak and Haven teams
have coordinated the relevant infrastructure specification aspects.

Don't panic if your cluster is not compliant (yet), as your cluster will likely still be
capable of hosting Open Zaak.

Features and their :ref:`requirements <installation_prerequisites>`:

* A PostgreSQL database with the following extensions:

    - ``pg_trgm``
    - ``postgis``

* Load balancing over multiple replicas is supported using ``Deployment`` resources
* Fully stateless deployments without volumes are possible *if and only if* you do not
  use the Documents API backed by the local file system (the default). You can achieve
  this by using the CMIS-adapter or by using a Documents API from another vendor.
* If you use the Documents API backed by the local file-system, you need a
  ``ReadWriteMany``-capable persistent volume solution, even with a single replica.

**Topology**

Traffic from the ingress will enter Open Zaak at one or multiple `NGINX`_
reverse proxies. NGINX performs one of two possible tasks:

* pass the request to the Open Zaak application or
* send the binary data of uploaded files to the client

NGINX exists to serve uploaded files in a secure and performant way.  All other requests
are passed to the Open Zaak application containers.

The application containers communicate with a PostgreSQL database, which must be
provisioned upfront. Additionally, Redis is used for caching purposes.

.. _installation_kubernetes_helm:

Deploy using Helm
=================

If you're familiar with or prefer Helm_, there are community-provided Helm charts_
for Open Zaak and Open Notificaties.

.. note::

   These charts are contributed by the community on a best-effort basis. The Technical
   Steering Group takes no responsibility for the quality or up-to-date being of these
   charts.

Example:

.. code-block:: bash

    helm repo add open-zaak https://open-zaak.github.io/charts/
    helm repo update

    helm install open-zaak open-zaak/open-zaak \
        --set "settings.allowedHosts=open-zaak.gemeente.nl" \
        --set "ingress.enabled=true" \
        --set "ingress.hosts={open-zaak.gemeente.nl}"

.. _Helm: https://helm.sh
.. _charts: https://github.com/open-zaak/charts

.. _installation_kubernetes_ansible:

Deploy using Ansible
====================

The Open Zaak organization maintains an Ansible_ collection which supports deploying
on Kubernetes using the open_zaak_k8s_
role.

.. note:: We assume knowledge of Ansible playbooks in the rest of this section.

A sample deployment is included in the Open Zaak repository, pinned on the most recent
stable Open Zaak version.

Get a copy of the deployment configuration
------------------------------------------

You can either clone the https://github.com/open-zaak/open-zaak repository,
or download and extract the latest ZIP:
https://github.com/open-zaak/open-zaak/archive/main.zip


Install dependencies
--------------------

.. note::

   Next to Ansible itself, we need some additional dependencies to interact with K8s
   clusters. These are Python libraries you need to install. The requirements are
   specified in the sample deployment directory.

First, navigate to the correct directory. In the folder where you placed the
copy of the repository, change into the ``deployment`` directory:

.. code-block:: shell

    (env) [user@host]$ cd /path/to/open-zaak/deployment/

Install the required dependencies with ``pip``:

.. code-block:: shell

    (env) [user@host]$ pip install -r requirements.txt

Next, install the Ansible playbook dependencies:

.. code-block:: shell

    (env) [user@host]$ cd kubernetes
    (env) [user@host]$ ansible-galaxy collection install -r requirements.yml

Deploying the applications
--------------------------

Open Zaak ships with a sample playbook for the applications, ``apps.yml``, which

* installs Open Zaak
* installs Open Notificaties

You can run the Ansible-playbooks as-is (with some configuration through variables), or
use them as inspiration for manual deployment.

For a list of all the available variables, check the
`collection <https://github.com/open-zaak/ansible-collection>`_ roles.

**Configuring Open Zaak**

To deploy Open Zaak, some variables need to be set (in ``vars/open-zaak.yml``):

* ``openzaak_domain``: the domain name, e.g. ``open-zaak.gemeente.nl``
* ``openzaak_secret_key``: generate a key via.
  Make sure to put the value between single quotes!

You might want to tweak environment variables in order to
:ref:`provision a superuser<installation_provision_superuser>`.

**Configuring Open Notificaties**

To deploy Open Notificaties, some variables need to be set (in ``vars/open-notificaties.yml``):

* ``opennotificaties_domain``: the domain name, e.g. ``open-notificaties.gemeente.nl``
* ``opennotificaties_secret_key``: generate a key.
  Make sure to put the value between single quotes!

Next steps
==========

You may want to :ref:`customize the logging setup<installation_logging_customize>`. The
default setup should be sufficient to get started though.

To be able to work with Open Zaak, a couple of things have to be configured first,
see :ref:`installation_configuration` for more details.

.. _installation_kubernetes_updating:

Updating an Open Zaak installation using Ansible
================================================

.. warning::

    Make sure you are aware of possible breaking changes or manual interventions by
    reading the :ref:`development_changelog`!

Ensure you have the deployment tooling installed - see
:ref:`installation_kubernetes_ansible` for more details.

If you have an existing environment (from the installation), update it:

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

Next, to perform the upgrade, you run the ``apps.yml`` playbook exactly like the
initial installation:

.. code-block:: shell

    (env) [user@host]$ ./deploy.sh apps.yml

.. note::

    In the Kubernetes deployment setup, Open Zaak makes use of multiple replicas by
    default, and is set up to perform rolling releases. This means that the old version
    stays live until all new versions are running without errors.

    We make use of health checks and liveness probes to achieve this.

    This does mean that there's a brief window where clients may hit the old or new
    version at the same time - usually this shouldn't pose a problem.


.. links used in doc

.. _Kubernetes: https://kubernetes.io/
.. _Cloud Native: https://www.cncf.io/about/who-we-are/
.. _Haven: https://haven.commonground.nl/
.. _NGINX: https://www.nginx.com/
.. _Ansible: https://www.ansible.com/
.. _open_zaak_k8s: https://github.com/open-zaak/ansible-collection/tree/main/roles/open_zaak_k8s
