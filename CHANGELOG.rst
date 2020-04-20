Changelog
=========

1.2.0 (2020-04-20)
------------------

New feature release and a set of bugfixes included.

**Features**

* Update admin layout version
* #507 -- use the original filename when downloading a document from the admin
* Reworked configuration of external APIs
* Added option to specify your NLX outway location and network
* Added the ability to enable/disable APIs offered by Open Zaak
* Added the option to configure external APIs, optionally selecting services from the
  NLX network.
* Added support for custom OAS urls. **Note** that you need to add them manually
  in ``zgw_consumers.Service`` for existing APIs (you can do it in the admin).

**Bugfixes**

* Bumped a number of libraries to their latest security releases
* #511 -- fix saving of resultaattype if bewaartermijn is null
* #495 -- use correct page titles for api schemas per component
* #318 -- Fixed (BesluitType)Admin M2M relations so that they show content from the same
  catalogus only
* Fixed Document inhoud base64 validation
* Enabled pre-filling the informatieobjecttype in zaaktype-informatieobjecttype admin
* #532 -- fixed issue with ``Resultaattype.omschrijving_generiek`` not updating
* #551 -- ensure client credentials are deleted when an ``Applicatie`` is deleted in
  in the admin
* #543 -- fix error when trying to create a document in the admin
* Fixed creating a Zaaktype with partial ``referentieProces`` gegevensgroep
* #553 -- made Eigenschap.specificatie required in admin
* #557 -- fix handling of ``brondatumArchiefProcedure: null``
* #558 -- fixed ``ZaakBesluit`` ``DELETE`` calls
* #556 -- fixed admin crash for resultaattype when the related zaaktype does not have
  a selectielijst procestype set
* #559 -- fixed deploying Open Zaak on a subpath (as opposed to on its own (sub)domain)
* #554 -- fixed admin crash when related informatieobjecttypen/besluiten are not
  available for a given zaak.
* #562 -- fixed nested ``Eigenschap.specificatie`` being ignored

**Documentation**

* Documentation minimal version of required development tooling
* #299 -- Fixed notification documentation generation
* Updated PR template
* #534 -- updated documentation links in the API specs

1.1.1 (2020-03-13)
------------------

Bugfix release w/r to deployment and ADFS

* Added option to disable group sync in ADFS login. If the ADFS provider
  does not provide the group claim, this would otherwise reset the user
  groups you carefully configured.
* Updated single-server deployment to make sure the web-server can read
  and serve uploaded files through the Documenten API.

1.1.0 (2020-03-11)
------------------

New feature release. Note that this is **not** yet an implementation of the 1.1.x API
specs!

* Included playbooks for NLX deployment
* Added communication channels to the docs (i.e. - how to find/contact us!)
* Added ADFS support (i.e. you can now log in to the admin with ADFS)
* Fixed some deployment tooling

1.0.4 (2020-03-05)
------------------

Improved support for integration with other APIs, most notably BAG/BRT APIs from the
kadaster (see https://pdok.nl). This increases the usability of ZaakObject relations.

* Added api-test.nl badge - proves that Open Zaak is compliant with the
  *API's voor zaakgericht werken* standard
* Added small documentation improvements
* Updated notification setup instructions
* Added support for API authentication with a simple *API key* (such as BAG or BRT)
* Added support for URL transformation so that data-fetching is forced over NLX

1.0.3 (2020-02-25)
------------------

Fixed infrastructure on single-server where Open Zaak and Open
Notificaties run on the same machine.

1.0.2 (2020-02-19)
------------------

Bugfixes and usability improvements

* Improve selectielijst-resultaten display in ResultaatType admin (#480)
* Improved production description
* Fixed file permissions for installation on single-server (#481)

1.0.1 (2020-02-17)
------------------

Bugfixes from initial release

* Added version information to Docker image
* Added better admin validation in various places [prevent crashes]
* Updated some documentation
* Fixed Besluiten API spec defects
* Fixed rendering the admin detail pages for read-only resources
* Fixed the cache for resultaattypeomschrijvinggeneriek
* Updated to latest Django security release
* Improved help-text for read-only fields
* Fixed CI

1.0.0 (2020-02-06)
------------------

🎉 First release of Open Zaak.

Features:

* Zaken API implementation
* Documenten API implementation
* Catalogi API implementation
* Besluiten API implementation
* Autorisaties API implementation
* Support for external APIs
* Admin interface to manage Catalogi
* Admin interface to manage Applicaties and Autorisaties
* Admin interface to view data created via the APIs
* `NLX`_ ready (can be used with NLX)
* Documentation on https://open-zaak.readthedocs.io/
* Deployable on Kubernetes, single server and as VMware appliance
* Automated test suite
* Automated deployment

.. _NLX: https://nlx.io/
