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

    helm repo add maykinmedia https://maykinmedia.github.io/charts/
    helm repo update

    helm install <release-tag> maykinmedia/openzaak \
        --set "settings.allowedHosts=open-zaak.gemeente.nl" \
        --set "ingress.enabled=true" \
        --set "ingress.hosts={open-zaak.gemeente.nl}"

.. _Helm: https://helm.sh
.. _charts: https://github.com/maykinmedia/charts


.. links used in doc

.. _Kubernetes: https://kubernetes.io/
.. _Cloud Native: https://www.cncf.io/about/who-we-are/
.. _Haven: https://haven.commonground.nl/
.. _NGINX: https://www.nginx.com/
