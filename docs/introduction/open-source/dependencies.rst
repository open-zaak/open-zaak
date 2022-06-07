.. _introduction_open-source_deps:

Open Source dependencies
========================

Open Zaak would not be possible without a number of other Open Source dependencies.

Most notably, the backend is written in the Python_ programming language. We use the
Django_ framework to build the web-application (which includes the API of course) that
is Open Zaak.

The core elements for the API implementation are:

* `Django REST framework`_ (DRF), to implement the RESTful API
* `drf-yasg`_ to generate the API documentation in the form of OAS 3.0 specification
* `VNG-API-common`_, a re-usable library with some specific VNG/Dutch API tooling, built
  on top of DRF and drf-yasg

.. _Python: https://www.python.org/
.. _Django: https://www.djangoproject.com/
.. _Django REST framework: https://www.django-rest-framework.org/
.. _VNG-API-common: https://vng-api-common.readthedocs.io/en/latest/
.. _drf-yasg: https://drf-yasg.readthedocs.io/en/stable/

What about the dependencies that don't have a 1.0.0 version (yet)?
------------------------------------------------------------------

Good question!

Most libraries follow semantic versioning, which takes the form of ``A.B.c`` version
numbering. In this pattern, ``A`` is the major version, ``B`` is the minor version and
``c`` is the patch version. Roughly speaking, if ``A`` increments, you can expect
breaking changes. If ``B`` increments, the changes are backwards compatible fixes and
new features, and if ``c`` changes, it's purely a bugfix release.

Libraries with a version like ``0.x.y`` are usually considering not-stable yet - as long
as no ``1.0.0`` release has happened, the internal API can change, or the project may
never reach that "maturity" you'd want.

If you look at our requirements_, you will see a couple of libraries that don't have a
1.0.0 version (yet). So, why do we depend on them, and is there a risk of depending on
them? Below, you can find the mitigations/reasoning why we decided to depend on them
anyway, in alphabetical order.


* ``cmislib-maykin==0.7.4`` - this package is a fork of a Python 2 library implementing
  the CMIS bindings. Maykin Media (one of the Open Zaak service providers) ported it to
  Python 3 and maintains this fork.

* ``coreschema==0.0.4`` is a transitive dependency of ``coreapi`` and ``drf-yasg``,
  which are both well-maintained. It is made by the same author as DRF itself.

* ``dictdiffer==0.9.0`` is not mission-critical and can easily be swapped out if needed.
  It's currently used to visualize changes obtained from audit trail records in the
  admin interface. The library is Open Source on Github, and could be forked if needed.

* ``django-auth-adfs-db==0.3.0`` is an add-on for ``django-auth-adfs``. Maykin Media is
  one of the maintainers.

* ``django-db-logger==0.1.12`` is not mission-critical and can easily be swapped out if
  needed. The library is Open Source on Github, and could be forked if needed.

* ``django-extra-views==0.14.0`` is a popular Django package with a large community
  behind it. The original author is still active as well.

* ``django-sendfile2==0.6.1`` is a fork of django-sendfile, focusing on Python 3 support.
  The core functionality is very stable and unlikely to cause problems.

* ``djangorestframework-gis==0.18`` is used for the GeoJSON serialization. We only use
  a small set of features, but it's the go-to GIS library in combination with DRF, and
  very stable despite the version numbering.

* ``drf-nested-routers==0.93.3`` sees regular maintenance and activity on Github, with
  high popularity.

* ``drf-writable-nested==0.6.3`` sees regular maintenance and activity on Github, with
  high popularity.

* ``httplib2==0.20.4`` transitive dependency of the CMIS binding. Still maintained.

* ``inflection==0.5.1`` transitive dependency of drf-yasg, which is quite a popular
  project.

* ``iso-639==0.4.5`` stable package that just happens to never have been named 1.0.
  ISO-639 is an international standard, which don't tend to change.

* ``isodate==0.6.1`` yet another library to parse ISO-8601 dates. Transitive dependency
  of ``vng-api-common``.

* ``python-dotenv==0.19.2`` is a popular, actively maintained project on Github

* ``ruamel.yaml.clib==0.2.6`` transitive dependency of ``ruamel.yaml``, by the same author

* ``ruamel.yaml==0.17.21`` transitive dependency of drf-yasg, actively maintained.

* ``sqlparse==0.4.2`` direct dependency of Django. Given the widespread use of Django,
  this should not pose any problems.

* ``zgw-consumers==0.18.0`` library maintained by Maykin Media. Together with
  gemma-zds-client, preparations are in the works for a 1.0 version.

.. _`requirements`: https://github.com/open-zaak/open-zaak/blob/master/requirements/base.txt
