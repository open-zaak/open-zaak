# Mission statement
What: purpose of OpenZaak

OpenZaak wants to help Dutch municipalities and other government agencies to implement Zaakgericht Werken (ZGW, a Dutch form of case management for municipalities). Moreover it focuses on the registries that are necessary to store the data that is created and needed for ZGW.

Why OpenZaak

We believe that Zaakgericht Werken is a best practice for handling requests from citizens and companies. As such ZGW is a way of working that helps to efficiently organise the backoffice of municipalities on the one hand and to record data in a standardised way that is compliant with laws and regulations.

How: OpenZaak proposition

OpenZaak offers an open source software component for recording ZGW data in a standardised way. Data is stored and disclosed through standardised API's following the VNG standard "API's voor Zaakgericht Werken". OpenZaak includes administrative interfaces for IT operatives.


# Vision
We believe that Zaakgericht Werken helps Dutch municipalities to efficiently organise their work and to record and archive their data in a standardised way. The latter is the main concern of OpenZaak but cannot be achieved without a proper implementation of ZGW in the organisation. This is out of scope for OpenZaak.

OpenZaak fits fits within and complies to the Common Ground service oriented architecture ("vijflagenarchitectuur"). As a direct consequence of this architecture which enforces principles like "gegevens bij de bron" and "eenmalige opslag, meervoudig gebruik", there will be one and only one record (or file) of each case that is handled by a municipality. OpenZaak can be used for storing such records. While being in a transition to a Common Ground architecture, municipalities may have multiple OpenZaak instances (or other components that comply to "API's for Zaakgericht Werken"), but ultimately we envision only one such a repository per municipality for storing ZGW data.

OpenZaak is open source software. This means that everyone can use OpenZaak to deploy registries for ZGW. Also, everyone can inspect and modify the code of OpenZaak. We encourage this and welcome bug reports, feature requests, implementation reports and the like. OpenZaak will benefit from this, and can be improved.

OpenZaak complies to the "API's for Zaakgericht Werken". Features or changes that require changes to the standard are not added to OpenZaak before the standard is updated. The OpenZaak partners actively contribute bugs and user stories to the standard.


# Scope
The scope of OpenZaak is "Registries for ZGW" which means that we develop and maintain open source software for the storage and retrieval of ZGW data through standardised API's. This includes:

* Administrative interfaces for maintenance purposes
* Docker containers for deployment
* Documentation

OpenZaak conforms to and follows the standard "API's for Zaakgericht Werken". It includes the following API's:

* Catalogi API
* Zaken API
* Documenten API
* Besluiten API
* Notificaties API
* Autorisaties API

Open for discussion is whether it should be extended to include the new API's for Klantinteractie, i.e.:

* Contactmomenten API
* Verzoeken API
* Klanten API

