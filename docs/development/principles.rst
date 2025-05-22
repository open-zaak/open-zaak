.. _development_principles:

Principles and code style (draft)
=================================

Defining (architectural) principles and code style keeps the code base consistent
and manages expectations for contributions.

Backend
-------

On the backend, we use the `Django framework`_ and follow the project structure
of having apps within the project.

- Django apps contains models, views and API definitions. They group a logical part of
  the greater project which is loosely coupled to other apps.

  Tests are in the django app package. Split tests in logical modules, and try to avoid
  complex nesting structures.

- All apps must go in the ``src/openzaak`` directory, which namespaces all the Open Zaak
  code in the ``openzaak`` package. This prevents name conflicts with third party
  applications.

- Application names should always be in plural form.

- Components from the API standard go in ``openzaak.components.<component>``.

- Settings go in ``openzaak.conf``, which is split according to deploy environment:

      - dev
      - ci (Travis)
      - staging
      - production
      - docker

  Settings must always be defined in the ``openzaak.conf.includes.base`` or
  ``openzaak.conf.includes.api`` with sane defaults.

- Global runtime Open Zaak configuration (database backed) should go in the
  ``openzaak.config`` app.

- Generic tools that are used by specific apps should be a ``openzaak`` sub-package,
  or possibly go in ``openzaak.utils``.

- Integration with other, third-party services/interfaces should go in a
  ``openzaak.contrib`` package. This is currently (!) not the case yet.

- Code style and imports are enforced in CI with `ruff`_. 

Frontend
--------

- Javascript goes in the ``src/openzaak/js`` directory

- If possible, stick to Vanilla JS

- (Highly) dynamic interfaces are built using React_. Components should:

    - go in ``src/openzaak/js/components``
    - preferably use functional components with react hooks
    - aim to be prop-driven and keep as little local state as possible
    - be properly prop-type annotated
    - have default values for optional props

- Code should be linted and quality checked using ESLint_, with the AirBnB preset

- Browser support: latest and latest -1 version of the major browsers

.. _Django framework: https://www.djangoproject.com/
.. _ruff: https://github.com/astral-sh/ruff
.. _React: https://reactjs.org/
.. _ESLint: https://eslint.org/
