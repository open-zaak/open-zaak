.. _client-development-cors:

Cross-Origin Resource Sharing (CORS)
====================================

Some clients develop against Open Zaak using single-page-application technology that
runs completely in the browser, such as React, Angular or other frameworks.

Open Zaak must be deployed with an appropriate CORS-configuration for this.

.. note:: We always recommend using an API gateway/own backend to communicate with Open
   Zaak. It's simpler because you don't have to deal with CORS, and there's less risk
   of credentials/secrets leaking. You should **never** store client ID/secret in your
   dist bundle(s).

Production-grade settings
-------------------------

In production-like environments, we recommend using an explicit allow-list for the
trusted origins. This requires deploying Open Zaak with
``CORS_ALLOWED_ORIGINS=https://my-app.example.com``, where ``https://my-app.example.com``
is the domain where the application is deployed.

Development/experimental configuration
--------------------------------------

If you're running Open Zaak locally or on an environment with dummy data for
development purposes, you can grant CORS access to every possible client using
``CORS_ALLOW_ALL_ORIGINS=True`` in the Open Zaak deployment.

Separation of administrative interface and API
----------------------------------------------

The administrative interface authenticates using session cookies, while the APIs use
the ``Authorization`` header with bearer tokens.

The session cookies are never sent on cross-domain requests, and the CORS configuration
is configured to not allow credentials (which are typically session cookies). The API
with the ``Authorization`` header is not affected by this policy.
