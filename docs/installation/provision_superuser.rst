.. _installation_provision_superuser:

Provisioning a superuser
========================

A clean installation of Open Zaak has no existing data, it's up to the service provider
and/or the users to set up Open Zaak to your liking.

To be able to do anything in the Open Zaak admin interface, you need a user account
with sufficient permissions, typically a superuser. Open Zaak has a couple of mechanisms
to create this superuser.

Creating a superuser manually
-----------------------------

Superusers can be created through the :ref:`installation_reference_cli` built into Open
Zaak, for example:

.. code-block:: bash

    python src/manage.py createinitialsuperuser \
        --username admin \
        --password admin \
        --email admin@gemeente.nl \
        --no-input

This will create the user if it does not exist yet. If the user already exists (based
on username), nothing happens.

You can get detailed information by getting the built-in help:

.. code-block:: bash

    python src/manage.py createinitialsuperuser --help

.. note:: Instead of providing the password as an argument, you can also use an
   environment variable ``DJANGO_SUPERUSER_PASSWORD`` or use the flag
   ``--generate-password``. Generated passwords are e-mailed to the configured e-mail
   address.

Creating a superuser as part of the (initial) deployment
--------------------------------------------------------

It's possible to automatically provision a superuser as part of your regular deployment,
be it on Kubernetes, Docker or Podman or any other way. Behind the scenes, the
``createinitialsuperuser`` management command is executed (see
:ref:`installation_reference_cli` for more details).

To opt in to this behaviour, you must specify the following environment variables:

* ``OPENZAAK_SUPERUSER_USERNAME``: username of the superuser account to create. If the
  account already exists, nothing will happen.
* ``OPENZAAK_SUPERUSER_EMAIL``: e-mail address of the superuser account. Has a default
  value of ``admin@admin.org``.

The ``DJANGO_SUPERUSER_PASSWORD`` environment variable is optional, if provided, this
is the password that will be set for the superuser account.

The superuser will be created on container start-up, before the web-server starts.
