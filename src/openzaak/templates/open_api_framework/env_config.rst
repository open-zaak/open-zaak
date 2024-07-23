{% extends "open_api_framework/env_config.rst" %}

{% block intro %}
Open Zaak can be ran both as a Docker container or directly on a VPS or
dedicated server. It relies on other services, such as database and cache
backends, which can be configured through environment variables.
{% endblock %}

{% block extra %}

Initial superuser creation
--------------------------

A clean installation of Open Zaak comes without pre-installed or pre-configured admin
user by default.

Users of Open Zaak can opt-in to provision an initial superuser via environment
variables. The user will only be created if it doesn't exist yet.

* ``OPENZAAK_SUPERUSER_USERNAME``: specify the username of the superuser to create. Setting
  this to a non-empty value will enable the creation of the superuser. Default empty.
* ``OPENZAAK_SUPERUSER_EMAIL``: specify the e-mail address to configure for the superuser.
  Defaults to ``admin@admin.org``. Only has an effect if ``OPENZAAK_SUPERUSER_USERNAME`` is set.
* ``DJANGO_SUPERUSER_PASSWORD``: specify the password for the superuser. Default empty,
  which means the superuser will be created *without* password. Only has an effect
  if ``OPENZAAK_SUPERUSER_USERNAME`` is set.

Advanced application server options
-----------------------------------

Open Zaak uses `uWSGI`_ under
the hood, which can be configured with a myriad of options. Most of these can be
provided as environment variables as well. The following option is one you may need with Open Zaak.

* ``UWSGI_HTTP_TIMEOUT`` - defaults to 60s. If Open Zaak does not complete the request
  within this timeout, then uWSGI will error out. This has been observed with certain
  CMIS implementations causing slow requests where 60s is not sufficient.

Initial configuration
---------------------

Open Zaak supports ``setup_configuration`` management command, which allows configuration via
environment variables.
All these environment variables are described at :ref:`installation_configuration_cli`.

.. _uWSGI: https://uwsgi-docs.readthedocs.io/en/latest/Options.html
.. _Selectie Lijst: https://selectielijst.openzaak.nl/
{% endblock %}