.. _installation_configuration:

=======================
Open Zaak configuration
=======================

Before you can work with Open Zaak after installation, a few settings need to be
configured first.

.. _installation_configuration_sites:

Setting the domain
==================

In the admin, under **Configuration > Websites**, make sure to change the existing
``Site`` to the domain under which Open Zaak will be deployed (see
:ref:`the manual<manual_configuration>` for more information).

Configure Notifications API
===========================

Next, the Notifications for Open Zaak must be configured. Navigate to
**Configuration > Notificatiescomponentconfiguratie** and fill out the correct API root
URL for the Notifications API, for example: ``https://notificaties.gemeente.local/api/v1/``.

You must configure the credentials for this API too:

1. Make sure you have a ``client ID`` and ``secret`` pair for this API.
2. Navigate to **API Autorisaties > Externe API credentials**
3. Click **Externe API credential toevoegen** in the top right
4. Enter the same API root URL in the *API-root* field, e.g.
   ``https://notificaties.gemeente.local/api/v1/`` and give a human readable label, for
   example: *Notifications API*.
5. Enter the ``Client ID`` and ``secret`` from step 1
6. Provide a **User ID** - for example ``open-zaak-backend``. This is only used for
   (audit trail) logging.
7. Provide a human readable **User represenation**, such as ``Open Zaak backend``. This
   is also used only for (audit trail) logging.

Currently, Open Zaak does not require any webhook subscriptions. It will however
send notifications on various API actions.

Create an API token
===================

By creating an API token, we can perform an API test call to verify the succesful
installation.

Navigate to **API Autorisaties** > **Applicaties** and click on **Applicatie toevoegen**
in the top right.

Give the application a label, such as ``test`` or ``demo``, and fill out a demo
``client ID`` and ``secret``. Next, click on **Opslaan en opnieuw bewerken** in the
bottom right. The application will be saved and you will see the same page again. Now,
click on **Beheer autorisaties** in the bottom right, which brings you to the
:ref:`authorization management<manual_api_app_auth>` for this application.

1. Select *Catalogi API* for the **Component** field
2. Check the ``catalogi.lezen`` checkbox
3. Click **Opslaan** in the bottom right

On the application detail page, you can now select and copy the JSON Web Token (JWT)
shown under **Client credentials**, which is required to make an API call.

.. warning::
   The JWT displayed here expires after a short time (1 hour by default) and should not
   be used in real applications. Applictions should use the ``client ID`` and ``secret``
   pair to generate JWT's on the fly.

Making an API call
==================

We can now make an HTTP request to one of the APIs of Open Zaak. For this example, we
have used `Postman`_ to make the request.

Make sure to set the value of the **Authorization** header to the JWT that was copied
in the previous step.

Then perform a GET request to the list display of ``ZaakTypen`` (Catalogi API) - this
endpoint is accessible at ``{{base_url}}/catalogi/api/v1/zaaktypen`` (where
``{{base_url}}`` is set to the domain configured in
:ref:`installation_configuration_sites`).

.. figure:: assets/api_request.png
    :width: 100%
    :alt: GET request to Catalogi API

    A GET request to the Catalogi API using Postman

.. _Postman: https://www.getpostman.com/
