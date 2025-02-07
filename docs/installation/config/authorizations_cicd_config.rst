.. _installation_configuration_auth_cicd:

TODO move this to CLI

==============================================
Open Zaak authorizations configuration (CI/CD)
==============================================

In order to automate configuration of authorizations, it is possible to load authorizations
from a fixture. For example, this fixture can be generated on a test environment and loaded
on an acceptance environment, to avoid having to manually sync the two environments.

.. note::

    In order for the loading of authorization configuration to work properly, it is important that
    the catalogi and \*typen for which there are Autorisaties are also present in the
    target environment (e.g. acceptance) and that they have the **same** UUIDs as in the
    source environment.

    This can be ensured by importing catalogi and \*typen on your target environment and **unchecking**
    the option to generate new UUIDs (see the :ref:`manual <manual_import_export_catalogi>` for more information about import/export)

.. _authorization_config_generate_fixture:

Generating the fixture
----------------------

The following command can be run to generate a `.yaml` fixture file containing the authorization configuration.
This file will contain the following:

- Credentials (client IDs and secrets)
- ``Applicaties`` and their related ``Autorisaties`` (including autorisaties based on catalogi)

.. code-block:: bash

    docker exec <container-id> sh /dump_auth_config.sh > fixture.yaml

.. warning::

    Since the file produced by the above command contains client IDs and secrets, be sure to handle it
    with care! If this file is to be used in CI, make sure to encrypt it (e.g. with Ansible Vault) before checking it
    into version control

Loading the fixture
-------------------

In order to load this fixture in another environment, make sure the environment variables
described in :ref:`CLI configuration <ref_step_>` are configured correctly.

The domain mapping is a `.yaml` file used to correctly map the domains of different environments for
the URLs of zaak/besluit/informatiebjecttypen. An example of what this file can look like:

.. code-block:: yaml

    - acceptance: https://acc.openzaak.nl
      production: https://openzaak.nl
    - acceptance: https://external.acc.openzaak.nl
      production: https://external.openzaak.nl

In this example, in case this fixture is loaded on an instance with ``ENVIRONMENT=production``, the domain
``https://acc.openzaak.nl`` in all URLs is replaced with ``https://openzaak.nl`` and ``https://external.acc.openzaak.nl``
is replaced with ``https://external.openzaak.nl``.

Because loading this fixture is part of ``setup_configuration``, its execution is generic and is described
in :ref:`CLI configuration <setup_config_execution>`.

Some things to keep in mind:

* by default, when running the ``setup_configuration`` without ``--overwrite``, a check happens to
  check if all Applicatie UUIDs and client IDs are present already in the instance. If this is the
  case, the fixture is not loaded and nothing happens.

* if you always want the content of the fixture to be applied, make sure to run the ``setup_configuration``
  command with ``--overwrite``. This will ensure that the fixture is always loaded and any existing data
  will be updated.

* if you want to use the fixture as the single source of truth, you can set ``AUTHORIZATIONS_CONFIG_DELETE_EXISTING`` to ``True``.
  Do note that this will remove all existing Applicaties/autorisaties, credentials and CatalogusAutorisaties before loading the fixture.
  This option should only be used if this configuration is **not** managed via the admin or API.
