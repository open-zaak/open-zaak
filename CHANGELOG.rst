Changelog
=========

1.7.3 (2022-09-01)
------------------

Bugfix release

* [#1233] Fixed a crash when using single-sign on via OpenID Connect
* Fixed docker-compose setup (thanks Bart Jeukendrup)
* Bumped django and django-sendfile2 to latest security patches
* Applied workaround for large catalogus export crashes
* [#1228] Made response data for empty Zaak.verlenging uniform - now always
  returns ``null`` if there is no extension
* [#1247, #1248] Fixed datepicker calendar being hidden behind another layer in the UI
* [#1198] Fixed ``ordering`` parameter in ``zaak__zoek`` POST body not being respected

1.7.2 (2022-07-26)
------------------

Fixed some issues discovered when upgrading from 1.6 or older

* [#1227] Added missing OIO relation validation when using remote resources
* [#1213] Add missing migration for Status.Meta changes
* Fixed issue in migration order

1.7.1 (2022-07-19)
------------------

Open Zaak 1.7.1 fixes some bugs discovered in 1.7.0

* [#1211] Fixed not being able to create a new version of a published zaaktype
* [#1213] Made the ordering for zaak.status explicit

1.7.0 (2022-07-08)
------------------

Open Zaak 1.7.0 is a rather big feature release.

The biggest changes are:

* Updated Zaken API from 1.0.3 to 1.1.2
* Updated Catalogi API from 1.0.0 to 1.1.1
* Admin UI improvements

**New features**

* [#1109 and #1157] Implemented Zaken API 1.1.2 - please check the upstream VNG API standards for
  more information
* [#1109] Implemented Catalogi API 1.1.1 - please check the upstream VNG API standards
  for more information
* [#1145] the log level is now configurable through environment variables
* [#1105 and #1182] Improved performance of catalogus imports
* [#510] allow filtering zaaktypen on geldigheid and publish status
* [#970] improved the handling of selectielijst in zaaktypen/resultaattypen - the admin
  now protects you better from making invalid configurations
* [#1030] The selectielijst procestypes are now refreshed when the selectielijst-year
  is changed and the selectielijstklasse choices for a resultaattype are now updated
  if the zaaktype is changed or set
* [#1085] the admin now runs more extensive validation on zaaktype publish to prevent
  misconfiguration:

    - checks that there is at least one roltype
    - checks that there is at least one resultaattype
    - checks that there are at least two status types (initial + closing)
* [#1119] the Open Zaak version number is now displayed in the in admin footer
* [#1183] updated EN -> NL translations

**Bugfixes**

* [#1130] added missing error documents
* [#1107] aligned admin validation of resultaattype-archiefprocedure with API validation
* [#979] Prevent cascading deletes when deleting a zaaktype, which would delete related
  zaken before
* [#983] allow concept zaaktype updates with published documenttypes
* [#981] allow null for eindeGeldigheid in Catalogi API
* [#992] run deelzaaktype validation for zaak.hoofdzaak.zaaktype
* [#1023] fixed zaak list returning duplicated zaken
* [#1080] fixed displaying authorization (specs) if there are no related objects
  (zaaktype/documenttype/besluittype) yet
* [#1081] Added test to confirm autorisaties are deleted when documenttypes are deleted
* [#1169] Ensure the selectielijst procestype year is derived and stored when importing
  zaaktypen
* [#1042] Fixed a number of bypasses that allowed you to edit published zaaktypen
* [#1108] Fixed crash while validating document archival status on Zaak create

**Documentation**

* Documented the API parity policy - there are now procedures for adding experimental
  features to Open Zaak
* [#1001] restructurd deployment documentation
* Documented buildkit requirement in docker-compose install
* Updated documentation for which API versions Open Zaak implements

**Project maintenance**

* [#1129] Fixed the failing api-test.nl build
* [#1136 and #1207] Bump to the latest security releases of Django
* [#1139] Refactor ADFS/AAD usage to generic OIDC library
* Update to Python 3.9
* Improved test isolation in CI build
* Replace set_context with new context system DRF (ongoing work)
* Replace raw requests usage with Service wrapper
* Remove some duplicated/bad patterns in test code
* Upgraded PyJWT dependency
* Upgraded frontend dependencies for security issues
* Removed the zds-client library mocking utility usage
* Cleaned up requests mock usage to prevent real HTTP calls from being made
* Refactored API spec mocking in tests to remove duplication and custom code
* API spec references for data validation are now pinned to release tags rather than
  commit hashes
* Reduced docker build context and image size
* Upgraded to gemma-zds-client 1.0.1
* [#1099] Added ZGW OAS tests to CI pipeline

.. warning::

   Manual intervention required for ADFS/AAD users.

   Open Zaak replaces the ADFS/Azure AD integration with the generic OIDC integration.
   On update, Open Zaak will attempt to automatically migrate your ADFS configuration,
   but this may fail for a number of reasons.

   We advise you to:

   * back up/write down the ADFS configuration BEFORE updating
   * verify the OIDC configuration after updating and correct if needed

   Additionally, on the ADFS/Azure AD side of things, you must update the Redirect URIs:
   ``https://open-zaak.gemeente.nl/adfs/callback`` becomes
   ``https://open-zaak.gemeente.nl/oidc/callback``.

   In release 1.8.0 you will be able to finalize the removal by dropping the relevant
   tables.

1.6.0 (2022-03-31)
------------------

**New features**

* Upgraded to Django 3.2 LTS version (#1098)
* Confirmed support for Postgres 13 and 14 and Postgis 3.2

**Bugfixes**

* Fixed a crash in the validation path for "zaak sluiten" where the archive status of
  related documents is checked.
* Fixed missing JWT expiry validation for audittrail endpoints and nested zaak resources
* Real IP address detection in brute-force protection should be fixed if configured
  correctly (#643)
* Fixed a wrong name in the ``ROL`` list endpoint filter parameters
* Updated the Docker base images to use slim-bullseye instead of stretch (#1097)
* Fixed NLX integration after their breaking changes and removed a bunch of custom
  code in the process (#1082)
* Fixed real IP detection in the Access logs by relying on the ``NUM_PROXIES`` config
  var (#643)
* Fixesd styles broken by bootstrap css (#1122)

**Documentation**

* Fixed 1.5.0 release date in the changelog
* Updated the FFPC assessment to version 0.2.3
* Renamed the "product steering group" to "core" group (=kerngroep)
* Updated assessment content w/r to CI location and git tag PGP signing
* Update Standard for Public Code assessment w/r to version control
* Rewrote the Kubernetes deployment documentation (#854)
* Explicitly documented the Open Zaak service dependencies (with supported version ranges)
* Documented advice to flush the caches after update to 1.6 (#1120)
* Fixed broken URL/markup in docs

**Project maintenance**

* Upgraded a number of dependencies to be compatible with Django 3.2 (#1098)
* Upgraded most dependencies to their latest available versions (#1098)
* Improved test suite to not rely on real network calls (related to #644)
* Removed some unused dev-tooling
* Enabled the newer Docker buildkit on CI
* Handled the KIC -> KC component rename
* Removed Kubernetes cluster infrastructure code/playbooks/manifests - this is not the
  scope of Open Zaak (#854)
* Updated CI/test dependencies (#1098)
* Fixed Docker Hub and docs badges

.. warning::

   Manual intervention(s) required!

   **Admin panel brute-force protection**

   Due to the ugprade of a number of dependencies, there is a new environment variable
   ``NUM_PROXIES`` which defaults to ``1`` which covers a typical scenario of deploying
   Open Zaak behind a single nginx reverse proxy. However, on Kubernetes there is
   typically an nginx reverse proxy for file serving AND an ingress operating as reverse
   proxy as well, requiring this configuration variable to be set to ``2``. Other
   deployment layouts/network topologies may also require tweaks.

   Failing to specify the correct number may result in:

   * login failures/brute-force attempts locking out your entire organization because one
     of the reverse proxies is now IP-banned - this happens if the number is too low.
   * brute-force protection may not be operational because the brute-forcer can spoof
     their IP address, this happens if the number is too high.

   Please review the documentation for more information about this configuration
   parameter.

   **Flush the caches**

   Because of the Django 2.2 -> 3.2 upgrade in the dependencies, it's likely the
   implementation details of the caches have an effect making old cached data
   incompatible with the new Django version.

   Therefore we recommend flushing the caches and let them rebuild automatically.

   On the redis containers, you can do this by getting a shell in the container and
   run the command:

   .. code-block:: bash

       redis-cli flushall


1.5.0 (2021-11-25)
------------------

**New features**

* Drop privileges in container to not run as root user (#869). **See the warning below for
  possible manual intervention!**
* Added generic OpenID Connect integration (#1002)
* Implemented ``JWT_LEEWAY`` configuration option to account for clock drift (#796)
* Enabled database connection re-use, configurable via ``DB_CONN_MAX_AGE``
* Implemented configuration option to enable query logging for debugging purposes
* Added a number of useful links to the dashboard menu. Most notably, this includes
  the link to `sign up for early notices`_ to plan around security releases in advance (#830).

.. _sign up for early notices: https://odoo.publiccode.net/survey/start/086e0627-8bc0-4b65-8aa9-f6872aba89d0

**Bugfixes**

* Bumped dependencies to newer versions (old versions were known to have vulnerabilities)
* Performance improvements in Documenten API when using CMIS-adapter (#974, #985)
* Fixed process forking in container to run as PID 1 (ec51077c19d4aaef4262464fc7db19cdf9d4a82c)
* Fixed incorrect validation error code in Documents API
* Fixed missing remote ZaakInformatieObject/BesluitInformatieObject validation on
  ObjectInformatieObject delete operation
* Fixed ``identificatie`` validation in the admin interface (#890)
* Fixed broken zaak document link in admin interface (#911)
* Fixed broken built-in documentation (notifications sent by component, #980)
* Fixed autorisaties admin breaking when a lot of authorizations applied for an application (#860)
* Fixed geldigheid-overlap detection in API/admin for zaaktypen, informatieobjecttypen
  and besluittypen (#994)
* Fixed incorrect notifications being sent when a new zaaktype version is created (#1026)
* Fixed crash because of missing validation on unique-together (zaak, status.datumGezet)
  fields (#960)
* Fixed performance regression for API clients with "large" numbers of authorizations (#1057)
* Fixed a crash when the JWT ``user_id`` claim is ``null`` (#936)

**CI/CD - Deployment tooling - infrastructure**

* Renamed various codebase aspects from Travis to generic "CI" after moving to Github Actions
* Replaced Alfresco CI tooling with prebuild extension image (#931)
* Cleanup up codebase structure (#939)
* Improved Github action to detect changed files and optimized CI to only run the
  necessary parts
* Added CI check for fresh deploys with ``CMIS_ENABLED=1`` (#972)
* Various improvements to make tests more deterministic/isolated

**Documentation**

* Added missing authors to the authors list
* Fixed broken GCloud link
* Documented ``UWSGI_HTTP_TIMEOUT`` environment variable
* Documented need to synchronized clocks (#796)

**Removed features**

* Removed NLX inway configuration integration (#949, #1061)
* Removed some deployment stuff not directly related to Open Zaak (NLX, ingress)

.. warning::

   Manual intervention required!

   Open Zaak 1.5.0+ corrected an oversight where the container was running as root. This
   is no longer the case, the image from 1.5.0 and newer drops to an unprivileged user
   with User ID 1000 and Group ID 1000.

   The actions you need to take are documented explicitly in the 1.5
   :ref:`upgrade notes <installation_reference_1_5_upgrade>`. Please read these
   before attempting the upgrade - we have documented them for the various platforms
   and deployment strategies.

1.4.0 (2021-04-30)
------------------

**New features**

* Updated ADFS-integration support, now Azure AD is properly supported
* Allow selection of internal zaaktypen for related zaaktypen with user friendly
  picker (#910)
* Removed the need to register internal services as external services when using
  CMIS adapter (#938)
* More CMIS-adapter optimization

    * caching of WSDLs
    * use connection pooling for CMIS requests (#956)

* Added support for initial superuser creation via environment variables (#952)

**Bugfixes**

* Updated to Zaken API 1.0.3 specification, see the upstream `1.0.3 changelog`_.

    * ``rol_list`` operation querystring parameter fixed, from
      ``betrokkeneIdentificatie__vestiging__identificatie`` to
      ``betrokkeneIdentificatie__organisatorischeeenheid__identificatie``

* Fixed missing metadata in CMIS-adapter interface (#925)
* Improved test isolation, reducing Heisenbugs
* Improved display of catalogi without explicit name so that they're clickable in the
  admin (#891)
* Fixed broken zaaktype export for published zaaktypen (#964)

**Deployment tooling / infrastructure**

* Added configuration parameter to opt-in to use ``X-Forwarded-Host`` headers to
  determine the canonical domain of a request to Open Zaak. This is particularly useful
  when using Istio sidecars for example. (#916)
* Improved dependency management script
* Added CI check to detect improper version bumping
* Bumped version of Django Debug Toolbar to fix an SQL injection. Safe in production, as
  this dependency is not included in the published Docker images.
* Fixed deleting a Zaak with related documents with CMIS-adapter enabled (#951)

**Documentation**

* Documented advice to service providers to sign up to the OpenZaak Release Early Notice
  List and mailing list (#915)
* Updated maturity document (FFPC, #681)
* Improved post-install configuration documentation (#947)
* Documented RabbitMQ's need for minimum of 256MB RAM

**External dependency cleanup**

* Dropped nlx-url-rewriter, see manual intervention below
* Dropped drf-flex-fields, it was not used
* Upgraded Django, djangorestframework, djangorestframework-camel-case, drf-yasg & other
  related packages (#935)
* Replaced django-better-admin-arrayfield fork with upstream again
* Replaced deprecated node-sass (and libsass) with dart-sass (#962)
* Bumped a number of dependencies to their latest release to get security fixes. None
  of the vulnerabilities appeared to impact Open Zaak, but better safe than sorry.

.. warning::

   Manual intervention required

   If you're upgrading from an *older* version than 1.2.0 of Open Zaak and using NLX,
   you need to update to 1.3.5 first, and then update to the 1.4.x series.

   In 1.2.0, the configuration of external API's was reworked, migrating from the
   nlx-url-rewriter package to zgw-consumers. In 1.4.0, the nlx-url-rewriter package
   is dropped and no longer present.

.. _1.0.3 changelog: https://github.com/VNG-Realisatie/zaken-api/blob/stable/1.0.x/CHANGELOG.rst#user-content-103-2021-03-29

1.3.5 (2021-03-25)
------------------

1.3.5 is another release focused on bugfixes, performance and quality of life.

**Bugfixes**

* Bumped ``cryptography`` and ``httplib2`` versions, which had some vulnerabilities
  (#856, #858, #859)
* Fixed an issue where documents were considered external when the CMIS-adapter is
  enabled (#820)
* Various fixes focused on improving the CMIS-adapter performance (#900, #881, #895)
* Bumped a number of dependencies to stable versions
* Dropped DB constraint preventing versioning of informatieobjecttypen to work as
  intended (#863)
* Fixed a crash when creating zaaktypen because of too-optimistic input validation (#850)
* Fixed a crash when using invalid query parameters when filtering the list of zaaktypen/
  informatieobjecttypen/besluittypen and related objects (#870)
* Mutations in the catalogi admin environment now send notifications similarly to how
  the same operations in the API would do (#805)
* Fixed filtering ``ZaakInformatieObjecten`` with CMIS enabled (#820)
* Fixed a crash when updating ``Zaaktype.gerelateerdeZaken`` (#851)
* Fixed incorrect and unexpected Autorisaties API behaviour for applications that are
  not "ready yet"

    * applications must have either ``heeftAlleAutorisaties`` set or have ``autorisaties``
      related to them (cfr. the standard)
    * applications not satisfying this requirement are not visible in the API (for read,
      write or delete)
    * applications not satisfying this requirement are flagged in the admin interface and
      can be filtered
    * when (zaak)typen are deleted, they're related autorisaties are too. If this leads
      to an application without autorisaties, the application is also deleted as it is
      no longer valid

* Fixed serving files for download when using CMIS-adapter and dealing with ``BytesIO``
  streams in general (#902)

**Deployment tooling / infrastructure**

* Uses new version of deployment tooling with podman support (alternative to Docker
  runtime)
* Fixed and improved configuration of the Notifications service in the
  ``setup_configuration`` management command. Generated credentials are now written
  to ``stdout`` and need to be used to configure Open Notificaties (or alternatives).
* Bumped to newer versions of Django and Jinja2, including bug- and security fixes
  (#906, #907)

**Documentation**

* Link to the mailing list added to the security documentation
* On the Github issue template you're now asked to specify which Open Zaak version
  you're using
* Updated Standard for Public Code checklist w/r to security procedures (#864)
* Documented the project dependencies with versions < 1.0 (#681)
* Updated the feature request template on Github
* Documented which security-related headers are set by the application and which on
  webserver level.
* Updated Standard for Public Code checklist w/r to using Open Standards (#679)

**New features**

* Added support for self-signed certificates, especially where Open Zaak consumes
  services hosted with self-signed (root) certificates. See the documentation on
  readthedocs for full details and how to use this. (#809)

**Cleanup**

* Removed unused and undocumented newrelic application performance monitoring integration
* Updated to pip-tools 6 to pin/freeze dependency trees

1.3.4 (2021-02-04)
------------------

A regular bugfix release.

**Bugfixes**

* Fixed incorrect protocol used in notification payloads (#802)
* Improved test suite determinism (#813, #798)
* Fixed deleting documents when CMIS is enabled (#822)
* Fixed Open Zaak compatibility with an external Documenten API

    * Fixed error logging interpolation (#817)
    * Fixed transaction management (#819)
    * Fixed some django-loose-fk bugs
    * Fixed deleting the remote ObjectInformatieObject on cascading zaak-destroy
      operations
    * Fixed ``Besluit.zaak`` nullable behaviour - now an empty string is returned
      correctly

* CMIS adapter fixes

    * Implemented Documenten API URL shortening for use with select CMIS DMSs
    * Fixed an oversight where ``Gebruiksrechten`` were not updated in the CMIS
      repository

* Removed notifications for ZIO (partial) update & destroy - the standard only
  prescribes ``create`` notifications.
* Fixed running the test suite with the ``--keepdb`` option
* Bumped a number of (frontend) dependencies following Github security notices
* Throw a command error when testing the notifications sending before correctly
  configuring the Notifications API (#667)
* Fixed Open-Zaak not accepting ``application/problem+json`` response media type in
  content negotation (#577)
* Fixed leaving "producten en diensten" blank in Zaaktype admin (#806)
* Increased the ``DATA_UPLOAD_MAX_NUMBER_FIELDS`` Django setting (#807)
* Fixed zaaktype/informatieobjecttype/besluittype publish action API documentation (#578)
* Fixed the handling of the ``SUBPATH`` environment variable (#741)

**Deployment tooling / infrastructure**

* Bumped to version 0.11.1 of the deployment tooling, which added support for:

    - flexibility in certificate configuration
    - enabled http2 in load balancer
    - improved support for additional environment variables
    - Red Hat and CentOS

* Fixed pushing the ``latest`` docker image tag to Docker Hub for builds on the master
  branch
* Open Zaak now provides Helm_ charts_ to deploy Open Zaak & Open Notificaties on
  Haven_ compliant clusters (thanks to @bartjkdp)

**Documentation**

* Fixed CI badges in READMEs
* Fixed example recipe for client application developers (#815)
* Documented the security issue process (#831)
* Added Contezza as service provider
* Removed (outdated) documentation duplication in README (#717)
* Removed ``raven test`` Sentry test command from documentation - we no longer use
  Raven but have switched to ``sentry_sdk`` instead (#721)
* Documented the need to register notification channels (#666)
* Improved & updated the API schema documentation
* Link to run-time behaviour documentation for each API component (#753)

**New features**

* Added bulk publishing options to the admin for zaaktype, informatieobjecttype and
  besluittype (#838)

.. _Helm: https://helm.sh/
.. _charts: https://github.com/open-zaak/charts
.. _Haven: https://haven.commonground.nl/

1.3.3 (2020-12-17)
------------------

Security and bugfix release

.. warning:: this release includes a security fix for `CVE-2020-26251`_, where Open Zaak
   had a possible vulnerable CORS configuration. It is advised to update as soon as
   possible. The severity is considered low, since we haven't been able to actually
   exploit this due to mitigating additional security configuration in other aspects.

.. _CVE-2020-26251: https://github.com/open-zaak/open-zaak/security/advisories/GHSA-chhr-gxrg-64x7

The bugfixes are mostly CMIS-adapter related.

**Bugfixes**

* The Cross-Origin Resource Sharing configuration is now safe by default - no CORS is
  allowed. Environment configuration options are made available to make CORS possible
  to varying degrees, which are all opt-in. This fixes CVE-2020-26251.
* Fixed duplicate ``ObjectInformatieObject`` instances being created with CMIS enabled
  (#778)
* Fixed stale CMIS queryset cache preventing correct chained filtering (#782)
* Fixed some links being opened in new window/tab without ``norel`` or ``noreferrer``
  set in the ``rel`` attribute
* Fixed multiple ``EnkelvoudigInformatieobject`` instances having the same
  ``bronorganisatie`` and ``identificatie`` (#768). If you're not using the CMIS-adapter,
  see the manual intervention required below.
* Fixed a bug retrieving ``ObjectInformatieObject`` collection in the Documenten API
  when CMIS is enabled. This may also have affected the ``Gebruiksrechten`` resource. (#791)

**Documentation**

* Improved documentation for CMIS services configuration
* Fixed a typo in the Governance document
* Documented environment variable to disable TLS certificate validation. This should
  never be used in production, instead the certificate setup should be fixed.

**Other changes**

* Enabled CMIS-adapter logging in DEBUG mode
* Migrated CI from Travis CI to Github Actions
* Explicitly test PostgreSQL versions 10, 11 and 12 (#716)
* Optimized CI build to re-use Docker image artifacts from previous jobs
* Replaced postman.io mocks subscription with nginx container (#790)
* Avoid some unnecessary queries when CMIS is enabled
* Implemented a (likely) fix to non-deterministic behaviour in the test suite (#798)

.. warning::

    Manual intervention required.

    There is a chance that documents have been created in the Documents API with
    duplicate ``(bronorganisatie, identificatie)`` combinations.

    We've provided a management command to check and fix these occurrences.

    Run ``python src/manage.py detect_duplicate_eio --help`` in an Open Zaak container
    to get the command line options. By default, the command is interactive:

    .. tabs::

      .. group-tab:: single-server

        .. code-block:: bash

            $ docker exec openzaak-0 src/manage.py detect_duplicate_eio
            Checking 30 records ...
            Found no duplicate records.

      .. group-tab:: Kubernetes

        .. code-block:: bash

            $ kubectl get pods
            NAME                        READY   STATUS    RESTARTS   AGE
            cache-79455b996-jxk9r       1/1     Running   0          2d9h
            nginx-8579d9dfbd-gdtbf      1/1     Running   0          2d9h
            nginx-8579d9dfbd-wz6wn      1/1     Running   0          2d9h
            openzaak-7b696c8fd5-hchbq   1/1     Running   0          2d9h
            openzaak-7b696c8fd5-kz2pb   1/1     Running   0          2d9h

            $ kubectl exec openzaak-7b696c8fd5-hchbq -- src/manage.py detect_duplicate_eio
            Checking 30 records ...
            Found no duplicate records.


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
kadaster (see https://www.pdok.nl). This increases the usability of ZaakObject relations.

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
