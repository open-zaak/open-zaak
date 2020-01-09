.. _manual_api_auth:

==================
API-toegang beheer
==================

Open Zaak biedt API's aan voor zaakgericht werken. Deze API's zijn niet toegankelijk
zonder authenticatie en autorisatie - gegevens worden namelijk correct beveiligd.
Eindgebruikers maken gebruik van (taak)applicaties, en het zijn deze applicaties die
gebruik maken van de API's voor zaakgericht werken.

Voordat een applicatie dus gegevens kan opvragen, opvoeren, bewerken of vernietigen,
moet deze applicatie hiervoor bekend zijn en geautoriseerd zijn.

Elke applicatie die aangesloten wordt op Open Zaak krijgt authenticatiegegevens.
Tegelijkertijd worden autorisaties ingesteld per applicatie. Autorisatiebeheerders
dienen vervolgens de applicatie-authenticatiegegevens te communiceren naar de
beheerder(s) van de (taak)applicatie.

.. warning::
    De applicaties/authenticatiegegevens die hier beheerd worden, zijn **niet**
    geschikt voor eindgebruikers, maar enkel voor server-to-server communicatie.

.. note:: Om API-toegang te kunnen beheren moet je tot de **API admin**
   groep behoren of equivalente permissies hebben. Zie
   :ref:`manual_users_groups` voor groepenbeheer.

.. _manual_api_auth_applicaties:

Een Applicatie registreren
==========================

Klik op het dashboard onder de groep **API Autorisaties** op de link **Toevoegen**
naast de kop **Applicaties**:

.. image:: assets/dashboard_add_application.png
    :width: 100%
    :alt: Dashboard voeg applicatie toe

Vul vervolgens het formulier in:

.. image:: assets/create_application.png
    :width: 100%
    :alt: Applicatieformulier

Het **label** is een vriendelijke naam voor de applicatie waarmee je kan herkennen om
welke applicatie binnen je organisatie het gaat. Je kan dit vrij kiezen.

Het vinkje **Heeft alle autorisaties** laat je toe om snel een applicatie alle mogelijke
rechten te geven. Merk op dat dit bijna altijd betekent dat een applicatie meer mag dan
nodig is!

Zorg ervoor dat je minstens één combinatie van *Client ID* en *Secret*
`genereert <https://passwordsgenerator.net/>`_. De applicatie heeft deze gegevens nodig
om tokens te kunnen genereren - communiceer deze dus op een veilige manier naar de
beheerder van de (taak)applicatie.

Klik tot slot op **Opslaan en opnieuw bewerken**, waarna je de
:ref:`autorisaties in kan stellen <manual_api_app_auth>`.

.. _manual_api_app_auth:

Instellen van de API-toegang voor een Applicatie
================================================
