# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test general API strategy guidelines.

Test the `national API guidelines`_ and/or the `DSO API guidelines`_. Just for
your information - the national guidelines are a result of the efforts done by
the DSO to compose API guidelines.

.. todo::

    a bunch of tests are defined, but skipped in upstream ZTC. They are for
    features that are not implemented yet:

    * ?expand parameter
    * ?fields parameter
    * Content-negotiation of documentation (HTTP_ACCEPT header)
    * ?sorteer parameter
    * ?zoek parameter
    * caching
    * rate limiting

.. _national API guidelines: https://github.com/Geonovum/KP-APIs
.. _DSO API guidelines: https://aandeslagmetdeomgevingswet.nl/digitaal-stelsel\
  /technisch-aansluiten/standaarden/api-uri-strategie/
"""
