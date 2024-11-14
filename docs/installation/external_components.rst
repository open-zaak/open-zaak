.. _installation_external_components:

Using external ZGW APIs
=======================

While Open Zaak itself implements all the necessary APIs for Zaakgericht Werken, it is possible
(conform the VNG standard) to use these APIs from *other components* than Open Zaak that
also implement the VNG standard(s).

For example, you might use an alternative implementation of the Documenten API. Using this
example, this guide describes the necessary configuration steps in Open Zaak.

1. Configure the credentials for the external Documenten API (so Open Zaak can access it):

   a. Navigate to **API Autorisaties > Services**
   b. Select Click **Service toevoegen**
   c. Fill out the form:

      - **Label**: For example: ``External Documenten``
      - **Service slug**: *For example:* ``external-documenten``
      - **Type**: Select the option: ``DRC (Informetieobjecten)``
      - **API root url**: the full URL to the external API root, e.g.
        ``https://documenten.gemeente.external/api/v1/``
      - **OAS url**: URL that points to the OpenAPI specification, e.g.
        ``https://documenten.gemeente.external/api/v1/schema/openapi.yaml``
      - **Authorization type**: Select the authorization used in the external API.
        For ZGW APIs it's ``ZGW client_id + secret``
      - **Client ID**: client ID for the external service. Should be provided
        by the external API administrators.
      - **Secret**: secret for the external service. Should be provided
        by the external API administrators.
      - **User ID**: Same as the Client ID
      - **User representation**: For example: ``Open Zaak``

   d. Click **Opslaan**.

2. Each of the local APIs should be included into **Services** configuration.
   In this example it should be Zaken, Catalogi and Besluiten APIs.
   For Catalog API:

   a. Navigate to **API Autorisaties > Services**
   b. Select Click **Service toevoegen**
   c. Fill out the form:

      - **Label**: For example: ``Local Catalogi``
      - **Service slug**: *For example:* ``local-catalogi``
      - **Type**: Select the option: ``ZTC (Zaaktypen)``
      - **API root url**: the full URL to the local Catalogi API root, e.g.
        ``https://open-zaak.gemeente.external/catalog/api/v1/``
      - **OAS url**: URL that points to the Catalogi API OpenAPI specification, e.g.
        ``https://open-zaak.gemeente.external/catalogi/api/v1/schema/openapi.yaml``
      - **Authorization type**: Select option ``ZGW client_id + secret``
      - **Client ID**: any client ID which was created in **API Autorisaties > Applicaties**
      - **Secret**: secret related to the client ID above
      - **User ID**: Same as the Client ID
      - **User representation**: For example: ``Open Zaak``

   d. Click **Opslaan**.

   Perform a-d steps for Zaken and Besluiten APIs. In the result there should be 3 external
   configurations for local APIs in **API Autorisaties > Services**

.. note:: The configuration of local APIs as external services exists as a temporary solution
          and would be removed. But for now it's required to include local APIs for the usage
          of external APIs.
