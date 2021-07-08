.. _development_howtos_dependencies:

Dependencies
============

Backend dependencies are managed with pip-tools_. pip-compile (part of pip-tools) takes
``*.in`` files with version constraints, and outputs the entire transitive dependency
tree to ``*.txt`` files.

The backend dependencies are layered:

- ``requirements/base.txt``: the minimal set of packages that is needed to run Open Zaak
  in a production-like environment
- ``requirements/ci.txt``: ``base.txt`` + any testing/CI tools to guard the quality of
  Open Zaak
- ``requirements/dev.txt``: ``ci.txt`` + developer tools only installed in a local
  environment to develop Open Zaak itself

Adding a backend dependency
---------------------------

Sometimes new features require new dependencies that aren't used yet in this project.

1. Open ``requirements/base.in``
2. Add the dependency in the right logical group
3. Run ``./bin/compile_dependencies.sh``
4. Commit the three changed ``requirements/*.txt`` files

For CI or development dependencies you add them to ``requirements/test-tools.in`` or
``requirements/dev.in`` respectively.

Upgrading a backend dependency
------------------------------

It happens that existing backend dependencies need to be upgraded (bugfixes, security
releases...). This is also done through ``./bin/compile_dependencies.sh``. Any extra
arguments supplied are forwarded to the underlying ``pip-compile`` calls.

1. Determine which package needs to be upgraded, for example Django
2. run ``./bin/compile_dependencies.sh -P django`` (substitute with appropriate package name)
3. Commit the changed ``requirements/*.txt`` files

This works for base, ci and dev dependencies.

.. note:: You can constraint versions, such as ``-P django~=2.2.0`` to get the latest
   patch version, or ``-P djangorestframework<3.13`` for example.

.. _pip-tools: https://pypi.org/project/pip-tools/
