.. _installation_configuration_cli:

=============================
Open Zaak configuration (CLI)
=============================

After deploying Open Zaak, it needs to be configured to be fully functional. The
command line tool ``setup_configuration`` assist with this configuration:

* It favours explicit configuration via options - you can integrate this with your
  infrastructure tooling such as init containers and/or Kubernetes Jobs
* In interactive mode, you receive prompts to fill out the requested information
* The command can self-test the configuration to detect problems early on

You can get the full command documentation with:

.. code-block:: bash

    src/manage.py setup_configuration --help

.. note::

    For more explanation/feedback, run the command with increased verbosity:

    .. code-block:: bash

        src/manage.py setup_configuration --verbosity 2


.. warning:: This command is declarative - if configuration is manually changed after
   running the command and you then run the exact same command again, the manual
   changes will be reverted.

Preparation
===========

You should prepare the following information:

* organization name, e.g. ``ACME``
* domain name where Open Zaak is deployed, e.g. ``open-zaak.gemeente.local``
* Notifications API root, e.g. ``https://notificaties.gemeente.local/api/v1/``
* A Client ID for Open Zaak to the Notifications API, e.g. ``open-zaak-acme``
* A Client Secret for Open Zaak to the Notifications API, e.g. ``insecure-nrc-secret``
* A Client ID for the Notifications API to Open Zaak, e.g. ``notificaties-api-acme``
* A Client Secret for the Notifications API to Open Zaak, e.g. ``insecure-oz-secret``

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

Alternatively, you can skip the self-tests by using the ``--no-self-test`` flag.

The example command uses the example values from the preparation above:

.. code-block:: bash

    src/manage.py setup_configuration \
        -v 2 \
        --organization ACME \
        --domain open-zaak.gemeente.local \
        --create-notifications-api-app \
        --notifications-api-app-client-id notificaties-api-acme \
        --notifications-api-app-secret insecure-oz-secret \
        --notifications-api-root https://notificaties.gemeente.local/api/v1/ \
        --notifications-api-client-id open-zaak-acme \
        --notifications-api-secret insecure-nrc-secret \
        --self-test \
        --send-test-notification

.. note:: Due to a cache-bug in the underlying framework, you need to restart all
   replicas for part of this change to take effect everywhere.

.. note:: You can output the results as JSON which your configuration management can
   then pick up and process:

   .. code-block:: bash

      export LOG_LEVEL=CRITICAL
      src/manage.py setup_configuration \
        ...\
        --skip-checks \
        --json

   The ``LOG_LEVEL`` environment variable ensures your output is not cluttered with
   logs, while ``--skip-checks`` prevents system check output from appearing.

Register notification channels
------------------------------

Before notifications can be sent to ``kanalen`` in Open Notificaties, these ``kanalen``
must first be registered via Open Zaak.

Register the required channels:

.. code-block:: bash

    python src/manage.py register_kanalen
