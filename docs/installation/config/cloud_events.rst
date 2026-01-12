.. _cloud_events_configuration:

========================
Configuring cloud events
========================

Open Zaak has experimental support for sending cloud events (see :ref:`cloud_events` for more information).
In order to make sure these events are sent, some configuration is required.

.. TODO:: Once cloud events are routed to Open Notificaties, make sure this documentation is updated accordingly

1. Make sure the ``ENABLE_CLOUD_EVENTS`` environment variable is set to ``True`` (see :ref:`installation_env_config`).
2. Make sure that PKIOverheid root certificate is added via the environment variable
   ``EXTRA_VERIFY_CERTS`` (see :ref:`installation_self_signed` for more information)
3. Navigate to ``/admin/config/cloudeventconfig/`` for your Open Zaak instance (the link to the cloud
   events configuration page is not yet visible in the admin dashboard, so currently the only way visit this page is to copy and paste this URL path).
4. Fill out the form:

    * Check the ``Enabled`` checkbox
    * Click the pencil icon to configure a ``Webhook service`` and fill in the following fields:

        * ``Label``: e.g.: ``Mijn Overheid``
        * ``Type``: select ``ORC (Overige)``
        * ``Api root url``: enter the URL of the API of Mijn Overheid
        * ``Authorization type``: select ``OAuth2 client credentials flow``
        * ``Client id``: enter the client id as received from Logius
        * ``Secret``: enter the secret as received from Logius
        * ``OAuth2 token url``: enter the URL of the Logius authentication server token endpoint
        * (Optional if mutual TLS is required): ``Client certificate`` click the ``+`` icon:

            * ``Label``: e.g. ``client certificate for Logius``
            * ``Type``: ``Key-pair``
            * ``Public certificate``: upload the public certificate to be used for mTLS
            * ``Private key``: upload the private key to be used for mTLS

    * ``Webhook path``: set this to ``/``
    * ``Cloud event source``: set this to the desired ``source`` to be used for cloud events (e.g. ``urn:nld:oin:01823288444:zakensysteem``)