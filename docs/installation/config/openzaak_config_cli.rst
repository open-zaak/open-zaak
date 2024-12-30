.. _installation_configuration_cli:

=============================
Open Zaak configuration (CLI)
=============================

After deploying Open Zaak, it needs to be configured to be fully functional. The
command line tool `setup_configuration`_ assist with this configuration:

You can get the full command documentation with:

.. code-block:: bash

    src/manage.py setup_configuration --help

.. warning:: This command is declarative - if configuration is manually changed after
   running the command and you then run the exact same command again, the manual
   changes will be reverted.

.. _`setup_configuration`: https://github.com/maykinmedia/django-setup-configuration/

Preparation
===========

The command executes the list of pluggable configuration steps, and each step
requires specific configuration information, that should be prepared.
Here is the description of all available configuration steps and the configuration
format, used by each step. Steps are run in the order stated here.


Sites configuration
-------------------

.. code-block:: yaml

    sites_config_enable: true
    sites_config:
      items:
      - domain: example.com
        name: Example site
      - domain: test.example.com
        name: Test site

More details about sites configuration through ``setup_configuration``
can be found at the _`site documentation`: https://github.com/maykinmedia/django-setup-configuration/blob/main/docs/sites_config.rst



Service Configuraiton
---------------------

All services are configured in a single step.
Full details can be found in the _`zgw-consumers documentation`: https://zgw-consumers.readthedocs.io/en/latest/setup_config.html

.. code-block:: yaml

    zgw_consumers_config_enable: true
    zgw_consumers:
      services:
      - identifier: notifications-api
        label: Notificaties API
        api_root: http://notificaties.local/api/v1/
        api_connection_check_path: notificaties
        api_type: nrc
        auth_type: api_key
        header_key: Authorization
        header_value: Token ba9d233e95e04c4a8a661a27daffe7c9bd019067

      - identifier: selectielijst-api
        label: Selectielijst API
        api_root: https://selectielijst.local/api/v1/
        ...




Notifications configuration
---------------------------

To configure sending notifications for the application ensure there is a ``services``
item present that matches the ``notifications_api_service_identifier`` in the
``notifications_config`` namespace:

.. code-block:: yaml

    notifications_config_enable: true
    notifications_config:
      notifications_api_service_identifier: notifications-api
      notification_delivery_max_retries: 1
      notification_delivery_retry_backoff: 2
      notification_delivery_retry_backoff_max: 3



Selectielijst configuration
---------------------------

To configure sending selectielijst for the application ensure there is a ``services``
item present that matches the ``selectielijst_api_service_identifier`` in the
``openzaak_selectielijst_config`` namespace:


.. code-block:: yaml

    openzaak_selectielijst_config_enable: true
    openzaak_selectielijst_config:
      selectielijst_api_service_identifier: selectielijst-api
      allowed_years:
        - 2025
        - 2026
      default_year: 2025


.. _setup_config_auth:

Authorization configuration
---------------------------

To Be implemented

.. _setup_config_oidc:

Mozilla-django-oidc-db
----------------------

Create or update the (single) YAML configuration file with your settings:

.. code-block:: yaml

   ...
    oidc_db_config_enable: true
    oidc_db_config_admin_auth:
    items:
      - identifier: admin-oidc
        oidc_rp_client_id: client-id
        oidc_rp_client_secret: secret
        endpoint_config:
          oidc_op_discovery_endpoint: https://keycloak.local/protocol/openid-connect/
   ...

More details about configuring mozilla-django-oidc-db through ``setup_configuration``
can be found at the _`documentation`: https://mozilla-django-oidc-db.readthedocs.io/en/latest/setup_configuration.html.


.. _setup_config_execution:

Execution
=========

Open Zaak configuration
-----------------------

With the full command invocation, everything is configured at once and immediately tested.

.. code-block:: bash

    src/manage.py setup_configuration --yaml-file /path/to/config.yaml


Register notification channels
------------------------------

Before notifications can be sent to ``kanalen`` in Open Notificaties, these ``kanalen``
must first be registered via Open Zaak.

Register the required channels:

.. code-block:: bash

    python src/manage.py register_kanalen
