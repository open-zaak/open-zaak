.. _installation_reference_containers:

Container configuration
=======================

Open Zaak is typically deployed as containers. There are some implementation details
relevant to properly configure this in your infrastructure.

Volumes
-------

Open Zaak defines the following paths as volumes. If no volume is mounted here, the
container software should create volumes to avoid writing to the container file system
layer.

* ``/app/private-media``
    Any files uploaded through the Documenten API (unless you use the CMIS adapter). In
    the future, it's possible that other authorization protected files will end up here.

* ``/app/media``
    Any files uploaded that are publicly available, think of files like municipality
    logos. This is currently not in active use.

* ``/app/log``
    Any logging configured to write to file (instead of stdout, the default).


Permissions
-----------

Open Zaak containers do not run as the root user, but instead drop privileges.


* Container user: ``openzaak``, with ``UID: 1000``
* Container user group: ``openzaak``, with ``GID: 1000``


**Docker**

Note that Docker mounts volumes as root, so you will need to correct the file system
permissions on those volumes. You can do this manually on the host system, or by deploying
a simple container (like ``busybox``) which runs as root to execute the ``chown`` command:

.. code-block:: bash

    chown -R 1000:1000 /app/private-media
    chown -R 1000:1000 /app/media
    chown -R 1000:1000 /app/log

**Kubernetes**

On Kubernetes, you can use the `pod security context`_ feature to ensure that the
volumes are writable by the Open Zaak container user.

.. code-block:: yaml

    securityContext:
      fsGroup: 1000  # should correspond to the container user group

.. note::

   Before Open Zaak 1.5.0, Open Zaak *did* run as root user. When upgrading
   existing installations, make sure to check your existing volumes and fix file system
   permissions if needed.

   As root, run:

   .. code-block:: bash

       chown -R 1000:1000 /app/private-media
       chown -R 1000:1000 /app/media
       chown -R 1000:1000 /app/log


.. _pod security context: https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#set-the-security-context-for-a-pod

.. _installation_reference_containers_celery:

Background tasks
----------------

Open Zaak uses `Celery`_ (an asynchronous task queue) to publish notifications. If
sending notifications is enabled (the default), then the task workers need to be running.

You can horizontally scale the workers by deploying more worker containers.

The ``docker-compose.yml`` in the root of the repository includes the example of Celery
worker container configuration.

.. _Celery: https://docs.celeryq.dev/en/stable/
