Changelog
=========

1.3.2 (2020-11-09)
------------------

Open Zaak 1.3.2 fixes a number of issues discovered in 1.3.1. Note that there are two
manual interventions listed below these patch notes. Please read them before updating.

**Changes**

* Added messages in the admin if the selectielijst configuration is invalid (#698)
* Applied a unique constraint on user e-mail address (if provided) (#589) - see manual
  intervention warning below.
* Upgraded to a newer version of ``zgw-consumers``, dropping the extra configuration
  field for services (#710)
* Implemented the upstream API bugfix, adding some zaken list query filters
  (https://github.com/VNG-Realisatie/gemma-zaken/issues/1686, #732)
* Added Github's code-scanning to detect vulnerable code patterns
* Updated frontend dependencies to secure versions
* Updated backend and deployment dependencies to secure versions (notably
  ``cryptography``) (#755, #756)
* [CMIS-adapter] Changed ``EnkelvoudigInformatieobject.identificatie`` generation. CMIS
  query does not (always) support ``LIKE`` queries, nor does it support aggregation
  queries (#762)

**Bugfixes**

* Fixed #711 -- changed ``Rol.omschrijving`` max_length from 20 -> 100
* Fixed input validation of binary document content (when the client forgets to base64
  encode it) (#608)
* Fixed primary keys being localized in admin URLs (#587)
* Fixed a crash when trying to download non-existant informatieobjecten (#584)
* Corrected validation of ``Eigenschap.lengte``. API and admin are now consistent, and
  decimals are now correctly interpreted (comma instead of dot) (#685)
* Fixed the ``register_kanaal`` management command auth-issue (#738)
* Fixed a bug where deleted zaaktypen had dangling ``Autorisatie`` records (#713) - see
  manual intervention warning below.
* Updated to `CMIS adapter 1.1.1`_ to fix some bugs (#760)

**Documentation**

* Update ``Governance.md`` after a number of steering group meetings
* Clarified that Ansible Galaxy roles and collections need to be installed separately
* Added a (technical) roadmap draft
* Drafted code style/code architecture principles
* Fixed a mix-up between authorizations/authentications API (#722)
* Docker image badge now points to Docker Hub
* Removed mention of Klantinteractie-API's - it's unclear what's being done with these
  API's
* Started documentation entries for developers of client/consumer applications

.. warning::

  Manual intervention required.

  E-mail addresses are used for logging in to the admin environment, which had no
  unique constraint. This is corrected in a database migration, which will crash if
  there are users with duplicate e-mail addresses. You should fix the duplicate
  addresses **BEFORE** updating.

.. warning::

    Manual intervention required.

    Some cleanup is required because of a synchronization bug. You need to run
    the following ``sync_autorisaties`` management command.

    .. tabs::

      .. group-tab:: single-server

        .. code-block:: bash

            docker exec openzaak-0 src/manage.py sync_autorisaties

      .. group-tab:: Kubernetes

        .. code-block:: bash

            $ kubectl get pods
            NAME                        READY   STATUS    RESTARTS   AGE
            cache-79455b996-jxk9r       1/1     Running   0          2d9h
            nginx-8579d9dfbd-gdtbf      1/1     Running   0          2d9h
            nginx-8579d9dfbd-wz6wn      1/1     Running   0          2d9h
            openzaak-7b696c8fd5-hchbq   1/1     Running   0          2d9h
            openzaak-7b696c8fd5-kz2pb   1/1     Running   0          2d9h

            $ kubectl exec openzaak-7b696c8fd5-hchbq -- src/manage.py sync_autorisaties

.. _CMIS adapter 1.1.1: https://github.com/open-zaak/cmis-adapter/blob/master/CHANGELOG.rst

1.3.1 (2020-08-31)
------------------

**Changes**

* Updated CMIS-adapter to 1.1 featuring support CMIS 1.0 Webservice binding and
  various new configuration options.
* Added support for configurable Selectielijst years to retrieve specific years
  from the Selectielijst API (#689)
* Prevent error monitoring from logging special personal data (#696)

**Bugfixes**

* Accept comma separated in ``EigenschapSpecificatie.waardenverzameling`` (#686)

**Documentation**

* Added SPDX license headers and check.
* Added Docker storage hint to make sure users run the Docker containers on
  volumes with enough disk space.

1.3.0 (2020-07-29)
------------------

Version 1.3.0 of Open Zaak introduces some new features, quality of life changes and
fixes bugs discovered in 1.2.0.

There is no 1.2.1 bugfix release. Upgrading from 1.2.0 to 1.3.0 requires no manual
intervention.

**What's new?**

* Added *experimental* support for CMIS backends for the Documenten API, as an
  alternative to Open Zaak database + filesystem. See the documentation for more details.
* Added a feature flag to allow unpublished ``*Typen`` to be used. This should only be
  used in Proof-of-concept environments, as it violates the VNG standard.
* Added a number of CLI commands for initial Open Zaak setup following installation. See
  the documentation for more details.
* Implemented extra ``zaak_list`` filters, added in 1.0.2 of the Zaken API standard
    - ``maxVertrouwelijkheidaanduiding``
    - ``betrokkene``
    - ``betrokkeneType``
    - ``omschrijvingGeneriek``
    - ``natuurlijk persoon BSN``
    - ``medewerker identificatie``

**Bugfixes and general QOL changes**

* Positioned the Foundation for Public Code and checked Open Zaak against their
  standard/guidelines
* The documentation now includes a Public Code checklist
* Added Code of Conduct
* Added Governance documentation
* Fixed running tests with ``--keepdb`` option
* Fixed the admin form for ``Zaaktype-Informatieobjecttype`` relation
* Fixed importing a ``Zaaktype-Informatieobjecttype`` with a ``Statustype`` relation
* Improved documentation for deploying on Kubernetes
* Added English version of README
* Fixed configuration form for external services when the NLX directory has not been
  configured (yet)
* Fixed ``BesluitType`` create in the admin (#594)
* Added and documented performance-profiling tooling for Open Zaak developers
* Fixed performance regression in ``zaak_list`` endpoint operation :zap:
* Fixed a crash on malformed UUIDs in endpoint URLs that expect a valid UUID 4 pattern
* Added the environment configuration reference to the published documentation
* Refactored notifications/selectielijst configuration to use the external services
  configuration
* Fixed ``EigenschapSpecificatie.waardenverzameling`` default value (empty list) (#611)
* Fixed missing validation on (zaaktype, eigenschapnaam) uniqueness
* Added Slack invite link
* Relaxed Resultaat.afleidingswijze validation in the admin too (see also ``6e38b865c``)
* Improved "Contributing" section

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
