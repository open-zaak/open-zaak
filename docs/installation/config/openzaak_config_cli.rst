.. _installation_configuration_cli:

=============================
Open Zaak configuration (CLI)
=============================

After deploying Open Zaak, it needs to be configured to be fully functional. The
command line tool ``setup_configuration`` assist with this configuration:

* It uses environment variables for all configuration choices, therefore you can integrate this with your
  infrastructure tooling such as init containers and/or Kubernetes Jobs.
* The command can self-test the configuration to detect problems early on

You can get the full command documentation with:

.. code-block:: bash

    src/manage.py setup_configuration --help

.. warning:: This command is declarative - if configuration is manually changed after
   running the command and you then run the exact same command again, the manual
   changes will be reverted.

Preparation
===========

The command executes the list of pluggable configuration steps, and each step
has required specific environment variables, that should be prepared.
Here is the description of all available configuration steps and the environment variables, 
used by each step. 

Sites configuration
------------------------

Configure the domain where Open Zaak is hosted

* ``SITES_CONFIG_ENABLE``: enable Site configuration. Defaults to ``False``.
* ``OPENZAAK_DOMAIN``:  a ``[host]:[port]`` or ``[host]`` value. Required.
* ``OPENZAAK_ORGANIZATION``: name of Open Zaak organization. Required.

Notification authorization configuration
----------------------------------------

Open Notificaties uses Open Zaak Autorisaties API to check authorizations
of its consumers, therefore Open Notificaties should be able to request Open Zaak

* ``NOTIF_OPENZAAK_CONFIG_ENABLE``: enable Notification credentials configuration. Defaults
  to ``False``.
* ``NOTIF_OPENZAAK_CLIENT_ID``: a client id, which Open Notificaties uses to request
  Open Zaak, for example, ``open-notificaties``. Required.
* ``NOTIF_OPENZAAK_SECRET``: some random string. Required.

Notification configuration
--------------------------

Open Zaak publishes notifications to the Open Notificaties.

* ``OPENZAAK_NOTIF_CONFIG_ENABLE``: enable Notification configuration. Defaults to ``False``.
* ``NOTIF_API_ROOT``: full URL to the Notificaties API root, for example
  ``https://notificaties.gemeente.local/api/v1/``. Required.
* ``NOTIF_API_OAS``: full URL to the Notificaties OpenAPI specification in YAML format.
* ``OPENZAAK_NOTIF_CLIENT_ID``: a client id, which Open Zaak uses to request Open Notificaties,
  for example, ``open-zaak``. Required.
* ``OPENZAAK_NOTIF_SECRET``: some random string. Required.

Selectielijst configuration
---------------------------

Open Zaak requests Selectielijst API in the Catalogi API component.
The Selectielijst API is not expected to require any authentication.

* ``OPENZAAK_SELECTIELIJST_CONFIG_ENABLE``: enable Selectielijst configuration. Defaults to ``False``.
* ``SELECTIELIJST_API_ROOT``: full url to the Selectielijst API root. Defaults to
  ``https://selectielijst.openzaak.nl/api/v1/``
* ``SELECTIELIJST_API_OAS``: full url to the Selectielijst OpenAPI specification in YAML format. Defaults to
  ``https://selectielijst.openzaak.nl/api/v1/schema/openapi.yaml``
* ``SELECTIELIJST_ALLOWED_YEARS``: years, for which process types can be used. Defaults to ``[2017, 2020]``.
* ``SELECTIELIJST_DEFAULT_YEAR`` = the default year from which process types will be used. Defaults to `2020`.

Demo user configuration
-----------------------

Demo user can be created to check if Open Zaak APIs work. It has superuser permissions, 
so its creation is not recommended on production environment.

* ``DEMO_CONFIG_ENABLE``: enable demo user configuration. Defaults to ``False``.
* ``DEMO_CLIENT_ID``: demo client id. Required.
* ``DEMO_SECRET``: demo secret. Required.

.. note:: You can generate these Client IDs and Secrets using any password generation
   tool, as long as you configure the same values in the Notifications API.

Execution
=========

Open Zaak configuration
-----------------------

With the full command invocation, everything is configured at once and immediately
tested. For all the self-tests to succeed, it's important that the
:ref:`Notifications API is configured <installation_configuration_notificaties_api>`
correctly before calling this command.

.. code-block:: bash

    src/manage.py setup_configuration


Alternatively, you can skip the self-tests by using the ``--no-selftest`` flag.

.. code-block:: bash

    src/manage.py setup_configuration --no-self-test


``setup_configuration`` command checks if the configuration already exists before changing it.
If you want to change some of the values of the existing configuration you can use ``--overwrite`` flag.

.. code-block:: bash

    src/manage.py setup_configuration --overwrite


.. note:: Due to a cache-bug in the underlying framework, you need to restart all
   replicas for part of this change to take effect everywhere.


Register notification channels
------------------------------

Before notifications can be sent to ``kanalen`` in Open Notificaties, these ``kanalen``
must first be registered via Open Zaak.

Register the required channels:

.. code-block:: bash

    python src/manage.py register_kanalen
