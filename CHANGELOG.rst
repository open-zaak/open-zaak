Changelog
=========

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
