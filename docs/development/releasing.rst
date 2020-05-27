
Release process
===============

Open Zaak makes use of quite a bit of Continuous Integration tooling to set up a full
release process, all driven by the Git repository.

Travis CI
---------

Our pipeline is mostly implemented on Travis:

Merges to the ``master`` branch are built on Travis, where:

1. Tests are run
2. Code quality checks are run
3. Compatibility with the *API's voor zaakgericht werken* standard spec is tested
4. The Docker image is built and published

If the build is for a Git tag on the ``master`` branch, then the image is built and
publish with that version tag to Docker Hub.

Releasing a new version
-----------------------

Releasing a new version can only be done by people with merge permissions to the master
branch belonging to the Open Zaak organisation on Github.

Assuming a current version of ``0.9.0``:

**Create a release branch**

.. code-block:: bash

    git checkout -b release/1.0.0

**Update the changelog**

Update ``CHANGELOG.rst`` in the root of the project, and make sure to commit the
changes.

**Bump the version**

.. code-block:: bash

    bumpversion minor

and commit:

.. code-block:: bash

    git commit -am ":bookmark: Bump version to 1.0.0"

Push the changes and make a pull request.

**Tag the release**

Once the PR is merged to master, check out the ``master`` branch and tag it:

.. code-block:: bash

    git checkout master
    git pull
    git tag 1.0.0

Tagging will ensure that a Docker image ``openzaak/open-zaak:1.0.0`` is published.

Releasing a dev-version
-----------------------

You can also make use of bumpversion to mark a release as a dev release:

.. code-block:: bash

    bumpversion dev

Which will take care of the ``major.minor.patch.devX`` suffix of ``devX``.
