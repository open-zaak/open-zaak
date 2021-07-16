.. _manual_oidc:

===========================
OpenID Connect configureren
===========================

Open Zaak ondersteunt Single Sign On (SSO) via het OpenID Connect protocol (OIDC) voor de beheerinterface.

Gebruikers kunnen op die manier inloggen op Open Zaak met hun account bij de OpenID Connect provider. In deze
flow:

1. Klikt een gebruiker op het inlogscherm op *Inloggen met OIDC*
2. De gebruiker wordt naar de omgeving van de OpenID Connect provider geleid (bijv. Keycloak) waar ze inloggen met gebruikersnaam
   en wachtwoord (en eventuele Multi Factor Authorization)
3. De OIDC omgeving stuurt de gebruiker terug naar Open Zaak (waar de account aangemaakt
   wordt indien die nog niet bestaat)
4. Een beheerder in Open Zaak kent de juiste groepen toe aan deze gebruiker als deze
   voor het eerst inlogt.

.. note:: Standaard krijgen deze gebruikers **geen** toegang tot de beheerinterface. Deze
   rechten moeten door een (andere) beheerder :ref:`ingesteld <manual_users>` worden. De
   account is wel aangemaakt.

.. _manual_oidc_appgroup:

Configureren van OIDC zelf
==========================

Contacteer de IAM beheerders in je organisatie om een *Client* aan te
maken in de omgeving van de OpenID Connect provider.

Voor de **Redirect URI** vul je ``https://open-zaak.gemeente.nl/oidc/callback`` in,
waarbij je ``open-zaak.gemeente.nl`` vervangt door het relevante domein.

Aan het eind van dit proces moet je de volgende gegevens hebben (on premise):

* Server adres, bijvoorbeeld ``login.gemeente.nl``
* Client ID, bijvoorbeeld ``a7d14516-8b20-418f-b34e-25f53c930948``
* Client secret, bijvoorbeeld ``97d663a9-3624-4930-90c7-2b90635bd990``

Configureren van OIDC in Open Zaak
==================================

Zorg dat je de volgende :ref:`gegevens <manual_oidc_appgroup>` hebt:

* Server adres
* Client ID
* Client secret

Navigeer vervolgens in de admin naar **Configuratie** > **OpenID Connect configuration**.

1. Vink *Enable* aan om OIDC in te schakelen.
2. Vul bij **Server (on premise)** het server adres in, bijvoorbeeld
   ``login.gemeente.nl``.
3. Vul bij **OpenID Connect client ID** het Client ID in, bijvoorbeeld
   ``a7d14516-8b20-418f-b34e-25f53c930948``.
4. Vul bij **OpenID Connect secret** het Client secret in, bijvoobeeld
   ``97d663a9-3624-4930-90c7-2b90635bd990``.
5. Vul bij **OpenID sign algorithm** ``RS256`` in.
6. Laat bij **OpenID Connect scopes** de standaardwaarden staan.

Vervolgens moeten er een aantal endpoints van de OIDC provider ingesteld worden,
deze zijn af te leiden uit het OIDC Discovery Endpoint
(``https://login.gemeente.nl/auth/realms/{realm}/.well-known/openid-configuration``)

7. Vul bij **JSON Web Key Set endpoint** het JWKS endpoint van de OpenID Connect provider in,
   meestal is dit ``https://login.gemeente.nl/auth/realms/{realm}/protocol/openid-connect/certs``.
8. Vul bij **Authorization endpoint** het authorization endpoint van de OpenID Connect provider in,
   meestal is dit ``https://login.gemeente.nl/auth/realms/{realm}/protocol/openid-connect/auth``.
9. Vul bij **Token endpoint** het token endpoint van de OpenID Connect provider in,
   meestal is dit ``https://login.gemeente.nl/auth/realms/{realm}/protocol/openid-connect/token``.
10. Vul bij **User endpoint** het user endpoint van de OpenID Connect provider in,
    meestal is dit ``https://login.gemeente.nl/auth/realms/{realm}/protocol/openid-connect/userinfo``.
11. Laat **Sign key** leeg.

Klik tot slot rechtsonder op **Opslaan**.

Je kan vervolgens het makkelijkst testen of alles werkt door in een incognitoscherm
naar https://open-zaak.gemeente.nl/admin/ te navigeren en op *Inloggen met OIDC* te
klikken.
