.. _cloud_events_configuration:

========================
Configuring cloud events
========================

Open Zaak has experimental support for sending cloud events (see :ref:`cloud_events` for more information).
These cloud events can be sent to Open Notificaties, which can route the events to subscribed
webhooks. In order to make sure these events are sent, some configuration is required in both
Open Zaak and Open Notificaties

Open Zaak
---------

1. Make sure the following environment variables are configured (see :ref:`installation_env_config`)

   * ``ENABLE_CLOUD_EVENTS``: set this to ``True``.
   * ``NOTIFICATIONS_SOURCE``: set this to the value that should be used in the ``source``
     field for cloud events (e.g. ``urn:nld:oin:01823288444:zakensysteem``).
   * ``SITE_DOMAIN``: set this to the primary domain Open Zaak is hosted on (e.g. ``open-zaak.gemeente.nl``).

2. Make sure the connection with Open Notificaties is configured via ``setup_configuration``.
   See :ref:`installation_configuration_cli` for more information.

Alternatively, if ``setup_configuration`` is not used for programmatic configuration,
the connection with Open Notificaties can be configured manually via the admin interface.
For more information on how to do this, see :ref:`installation_configuration`.

Open Notificaties
-----------------

For the required configuration in Open Notificaties, see :ref:`cloud_events_configuration_mijn_overheid`
