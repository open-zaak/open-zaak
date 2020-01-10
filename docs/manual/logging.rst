=======
Logging
=======

Sentry
======

To monitor and identify issues for Open Zaak, it is recommended to use `Sentry`_.
If Sentry is configured for Open Zaak, all exceptions that occur within the application
are sent to Sentry. For documentation on how to set up a project in Sentry, please refer to the official `documentation`_
(make sure to follow the instructions for the platform Python > Django).
After setting up the project, you will receive a **DSN**, which is the URL to which exceptions will be sent
(i.e. https://e95a42137e6042c59d19376e566f027a@sentry.openzaak.nl/104).
The created Sentry project can be linked to Open Zaak by setting
the environment variable ``SENTRY_DSN`` equal to this DSN.

.. _`sentry`: https://sentry.io/
.. _`documentation`: https://docs.sentry.io/guides/getting-started/

Different logs
==============

By default, Open Zaak has multiple loggers that log to different files.

- Nginx: in case Open Zaak is running in Docker, Nginx will log to standard output
  and the logs can be accessed using ``docker logs`` or ``kubectl logs`` (depending on the
  platform being used). In case of vmware appliance, the logs can be found in ``/var/logs/nginx/``
- uWSGI: by default uWSGI will log to standard output.
- Django: multiple loggers for Django are defined in the Open Zaak settings (``src/openzaak/conf/includes/base.py``),
  depending on which handler is used by which logger, the information will be logged to either the console
  or to the ``log/`` directory (files are automatically log-rotated so you will not run out of disk space).
- Docker: if Open Zaak is running in a Docker container, its logs can be retrieved by
  using the command ``docker logs <container_name>`` (see also `Docker documentation`_).

.. _`Docker documentation`: https://docs.docker.com/engine/reference/commandline/logs/
