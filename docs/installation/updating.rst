.. _installation_updating:

Updating an Open Zaak installation
==================================

Software receives new features and bugfixes all the time, and Open Zaak is no different.
At some point, you'll want to update to a newer version of Open Zaak - be it a patch
version with bugfixes or a feature release to upgrade to.

Before you actually upgrade, we strongly advise you to take a look at the
:ref:`development_changelog` to spot any breaking changes or required manual
interventions.

.. note::
    We always recommend you to have taken and tested your backups in case something
    goes wrong, BEFORE performing any updates.

.. note::
    We encourage having multiple environments such as staging and production, completely
    isolated from each other. This allows you to test out the update on a staging
    environment to check if anything goes wrong, without affecting production.

The update instructions are split per target environment.

Updating on Kubernetes
----------------------

See :ref:`deployment_kubernetes_updating` for the update instructions on Kubernetes.

Updating a single server installation
-------------------------------------

See the steps on how to
:ref:`update a single server installation<deployment_containers_updating>`.
