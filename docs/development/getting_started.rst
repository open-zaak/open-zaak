.. _development_getting_started:

===============
Getting started
===============

The project is developed in Python using the `Django framework`_. There are 3
sections below, focussing on developers, running the project using Docker and
hints for running the project in production.

.. _Django framework: https://www.djangoproject.com/

Installation
============

Prerequisites
-------------

You need the following libraries and/or programs:

* `Python`_ 3.7 or above
* Python `Virtualenv`_ and `Pip`_ 20.0 or above
* `PostgreSQL`_ 10.0 or above, with the `PostGIS-extension`_
* `Node.js`_ 10.0 or above
* `npm`_ 6.0 or above

.. _Python: https://www.python.org/
.. _Virtualenv: https://virtualenv.pypa.io/en/stable/
.. _Pip: https://packaging.python.org/tutorials/installing-packages/#ensure-pip-setuptools-and-wheel-are-up-to-date
.. _PostgreSQL: https://www.postgresql.org
.. _PostGIS-extension: https://postgis.net/
.. _Node.js: http://nodejs.org/
.. _npm: https://www.npmjs.com/


Getting started
---------------

Developers can follow the following steps to set up the project on their local
development machine.

1. Navigate to the location where you want to place your project.

2. Get the code:

   .. code-block:: bash

       $ git clone git@github.com:open-zaak/open-zaak.git
       $ cd open-zaak

3. Install all required libraries:

   .. code-block:: bash

       $ virtualenv env  # or, python -m venv env
       $ source env/bin/activate
       $ pip install -r requirements/dev.txt

4. Install the front-end CLI tool `gulp`_ if you've never installed them
   before and install the frontend libraries:

   .. code-block:: bash

       $ npm install
       $ npm run build

5. Activate your virtual environment and create the statics and database:

   .. code-block:: bash

       $ source env/bin/activate
       $ python src/manage.py migrate

6. Create a superuser to access the management interface:

   .. code-block:: bash

       $ python src/manage.py createsuperuser

7. You can now run your installation and point your browser to the address
   given by this command:

   .. code-block:: bash

       $ python src/manage.py runserver


**Note:** If you are making local, machine specific, changes, add them to
``src/openzaak/conf/includes/local.py``. You can also set certain common
variables in a local ``.env`` file. You can base these files on the
example files included in the same directory.

**Note:** You can run watch-tasks to compile `Sass`_ to CSS and `ECMA`_ to JS
using ``npm run watch``. By default this will compile the files if they change.

.. _ECMA: https://ecma-international.org/
.. _Sass: https://sass-lang.com/
.. _gulp: https://gulpjs.com/


Update installation
-------------------

When updating an existing installation:

1. Activate the virtual environment:

   .. code-block:: bash

       $ cd open-zaak
       $ source env/bin/activate

2. Update the code and libraries:

   .. code-block:: bash

       $ git pull
       $ pip install -r requirements/dev.txt
       $ npm install
       $ npm run build

3. Update the statics and database:

   .. code-block:: bash

       $ python src/manage.py migrate


Testsuite
---------

To run the test suite:

.. code-block:: bash

    $ python src/manage.py test openzaak

Configuration via environment variables
---------------------------------------

A number of common settings/configurations can be modified by setting
environment variables, add them to your ``.env`` file or persist them in
``src/openzaak/conf/includes/local.py``.

* ``SECRET_KEY``: the secret key to use. A default is set in ``dev.py``

* ``DB_NAME``: name of the database for the project. Defaults to ``open-zaak``.
* ``DB_USER``: username to connect to the database with. Defaults to ``open-zaak``.
* ``DB_PASSWORD``: password to use to connect to the database. Defaults to ``open-zaak``.
* ``DB_HOST``: database host. Defaults to ``localhost``
* ``DB_PORT``: database port. Defaults to ``5432``.

* ``SENTRY_DSN``: the DSN of the project in Sentry. If set, enabled Sentry SDK as
  logger and will send errors/logging to Sentry. If unset, Sentry SDK will be
  disabled.

Testing with CMIS adapter enabled
---------------------------------

The tests for Open Zaak with the CMIS adapter enabled use Alfresco as the Document Management System. This is run with docker compose, using the compose file
``docker-compose.travis-cmis.yml``. In the folder ``extension/``, there are xml files defining the custom models used.
The file ``config/alfresco-global.properties`` contains the global properties that are required to run Alfresco.

The containers are launched with:

    .. code-block:: bash

        $ docker-compose -f docker-compose.travis-cmis.yml up -d

This creates a ``volumes/`` directory where all the logs and the data are stored.

Settings
========

All settings for the project can be found in
``src/openzaak/conf``.
The file ``includes/local.py`` overwrites settings from the base configuration,
and is only loaded for the dev settings.
