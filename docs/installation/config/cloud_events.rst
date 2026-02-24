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

1. Make sure the ``ENABLE_CLOUD_EVENTS`` environment variable is set to ``True`` (see :ref:`installation_env_config`).
2. Make sure the ``NOTIFICATIONS_SOURCE`` environment variable is set, the value of this
   is used in the ``source`` field for cloud events (see :ref:`installation_env_config`).
3. Make sure the connection with Open Notificaties is configured via ``setup_configuration``.
   See :ref:`installation_configuration_cli` for more information.

Alternatively, if ``setup_configuration`` is not used for programmatic configuration,
the connection with Open Notificaties can be configured manually via the admin interface.
For more information on how to do this, see :ref:`installation_configuration`.

Open Notificaties
-----------------

For the required configuration in Open Notificaties, see :ref:`cloud_events_configuration_mijn_overheid`
