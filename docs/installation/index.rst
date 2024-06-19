.. _installation_index:

Installation
============

You can install Open Zaak in several ways, depending on your intended purpose and
expertise.

1. Deploy on :ref:`Kubernetes <installation_kubernetes>` for public testing and
   production purposes
2. Deploy on a :ref:`VM, VPS or dedicated server <installation_ansible>` with Docker
   Engine (or Podman) for public testing and production purposes
3. Run with :ref:`docker compose <installation_docker_compose>` on your computer for
   private testing purposes
4. Run from :ref:`Python code <development_getting_started>` on your computer for
   development purposes

Before you begin
----------------

.. note:: These requirements are aimed towards public testing and production
   deployments, though they are _interesting_ to understand the workings of Open Zaak.

* Check the :ref:`minimum system requirements<installation_hardware>` for the target
  machine(s).
* Ensure you have the :ref:`installation_prerequisites` available
* Make sure the target machine(s) have access to the Internet.
* The target machine(s) should be reachable via at least a local DNS entry:

  * Open Zaak: ``open-zaak.<organization.local>``
  * `Open Notificaties`_: ``open-notificaties.<organization.local>``

  The machine(s) do not need to be publically accessible and do not need a public DNS
  entry. In some cases, you might want this but it's not recommended. The same machine
  can be used for both Open Zaak and `Open Notificaties`_.

* If you want to use `NLX`_, make sure you have a publicaly available domain name, for
  example ``nlx.<organization.com>``, where your NLX-inway is accessible to the outside
  world.

.. _`Open Notificaties`: https://github.com/open-zaak/open-notificaties
.. _`NLX`: https://nlx.io/

Guides
------

.. toctree::
   :maxdepth: 1

   hardware
   prerequisites
   docker_compose
   kubernetes
   single_server
   provision_superuser
   config/index
   self_signed
   post_install
   updating
   external_components

Reference
---------

.. toctree::
   :maxdepth: 1

   reference/cli
   reference/logging
   reference/containers
   reference/fq-urls
   reference/time
   reference/1-5_upgrade
   reference/import
