.. _installation_index:

Installation
============

There are several ways to install Open Zaak. A scalable solution is to use
:ref:`Kubernetes<deployment_kubernetes>`. You can also run the
:ref:`Docker containers<deployment_containers>` on a single machine.

Before you begin
----------------

* Check the :ref:`minimum system requirements<installation_hardware>` for the target
  machine(s).
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
   deployment/kubernetes
   deployment/single_server
   config/index
   post_install
   updating
   extra/index
