=======
Logging
=======

Sentry
======

To monitor and identify issues for OpenZaak, it is recommended to use `Sentry`_.
If Sentry is configured for OpenZaak, all exceptions that occur within the application
are sent to Sentry. For documentation on how to set up a project in Sentry, please refer to the official `documentation`_.
After setting up the project, you will receive a **DSN**. The created Sentry project can be linked to OpenZaak by setting
the environment variable ``SENTRY_DSN`` equal to this DSN.

.. _`sentry`: https://sentry.io/
.. _`documentation`: https://docs.sentry.io/error-reporting/quickstart/?platform=javascript

Different logs
==============

By default, OpenZaak has multiple loggers that log to different files.

- Nginx: logs produced by Nginx can be found in the ``log/nginx/`` directory.
- uWSGI: by default uWSGI will log to standard output.
- Django: multiple loggers for Django are defined in the OpenZaak settings (``src/openzaak/conf/includes/base.py``),
  dependent on the handler used by the logger, the information will be logged to either the console
  or to the ``log/`` directory (a rotating file handler is used for the latter).
- Docker: if OpenZaak is running in a Docker container, its logs can be retrieved by
  using the command ``docker logs <container_name>`` (see also `Docker documentation`_).

.. _`Docker documentation`: https://docs.docker.com/engine/reference/commandline/logs/
