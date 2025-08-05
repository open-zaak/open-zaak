.. _installation_reference_1_5_upgrade:

Open Zaak 1.5 upgrade
=====================

Open Zaak 1.5.0+ corrected an oversight where the container was running as ``root``. This
is no longer the case, the image from 1.5.0 and newer drops to an unprivileged user
with User ID 1000 and Group ID 1000.

.. warning:: The Open Zaak 1.5 update has an impact on existing installations!

If you are using the Documenten API with the default Open Zaak storage (so, not the
CMIS adapter), then the directories in the storage are owned by the ``root`` user (or
the user that the container ``root`` user maps to, in the case of podman for example).

After dropping privileges in the new version, this means that Open Zaak and nginx
no longer have (write) access to these directories and files.

We have updated the deployment tooling to correct this where possible, but it's
impossible to cover every case.

The instructions on what to check on how to handle this are provided below per
supported environment.

**We strongly advise to backup your data and test this upgrade on a test/staging
environment before rolling it out in production!**

Kubernetes
----------

.. tabs::

  .. group-tab:: Helm

     We have added an init container to the Helm charts by default to fix the file
     system permissions. For this you need to:

     * update the Open Zaak chart version to at least 0.5.0
     * have ``persistence`` enabled
     * check if there are any :ref:`installation_reference_1_5_upgrade_cloud_provider_notes`

     Once the upgrade is performed, you can skip this init container by setting the
     ``initContainers.volumePerms=false`` value.

     Note that the Open Notificaties update also requires a Helm chart version update
     to ``0.5.0``.


.. _installation_reference_1_5_upgrade_cloud_provider_notes:

Cloud provider specific notes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not all cloud providers are the same. The three big ones are arguably Azure, AWS and
Google Cloud. Where applicable, we have provider-specific notes.

.. tabs::

    .. group-tab:: Azure

        **Storage classes**

        Persistent volumes on Azure are tricky. Out of the box only the
        ``kubernetes.io/azure-file`` provisioner works with ``ReadWriteMany`` mount
        mode, which Open Zaak requires.

        However, this filesystem gets mounted as ``root`` by default and it's not possible
        to correct the file permissions via an init container or the
        ``securityContext.fsGroup`` option. You must use a storage class with the
        correct mount options, for example:

        .. code-block:: yaml

            kind: StorageClass
            apiVersion: storage.k8s.io/v1
            allowVolumeExpansion: true
            reclaimPolicy: Delete
            volumeBindingMode: Immediate
            metadata:
              name: azurefile-openzaak
            provisioner: kubernetes.io/azure-file
            parameters:
              skuName: Standard_LRS
            mountOptions:
            - uid=1000
            - gid=1000

        Note the explicit ``uid`` and ``gid`` mount options which map to the user that
        Open Zaak runs as. For more information, see also
        `this related Kubernetes issue <https://github.com/kubernetes/kubernetes/issues/54610>`_.

        In our own testing, upgrading worked out of the box because the mounted volume
        results in ``777`` file permissions mode, while still being owned by the root
        user, which is functional but may not be what you want.

        .. note::

            On an existing installation you will probably have an existing PVC with
            incorrect mount options and changing the storage class after creation is
            not possible.

            We recommend backing up the uploaded files, deleting the PVC, modifying the
            storage class that Open Zaak uses and the restoring the backed up data on
            the new PVC.

    .. group-tab:: AWS

        No known challenges at the moment.

    .. group-tab:: Google Cloud

        No known challenges at the moment.
