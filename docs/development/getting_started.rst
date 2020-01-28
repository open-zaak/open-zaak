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
* Python `Virtualenv`_ and `Pip`_
* `PostgreSQL`_ 10 or above, with the `PostGIS-extension`_
* `Node.js`_
* `npm`_

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

       $ virtualenv env
       $ source env/bin/activate
       $ pip install -r requirements/dev.txt

4. Install the front-end CLI tool `gulp`_ if you've never installed them
   before and install the frontend libraries:

   .. code-block:: bash

       $ npm install -g gulp
       $ npm install
       $ gulp sass

5. Activate your virtual environment and create the statics and database:

   .. code-block:: bash

       $ source env/bin/activate
       $ python src/manage.py collectstatic --link
       $ python src/manage.py migrate

6. Create a superuser to access the management interface:

   .. code-block:: bash

       $ python src/manage.py createsuperuser

7. You can now run your installation and point your browser to the address
   given by this command:

   .. code-block:: bash

       $ python src/manage.py runserver

8. Create a .env file with database settings. See ``.env-example`` for an
   example:

   .. code-block:: bash

       $ cp .env-example .env


**Note:** If you are making local, machine specific, changes, add them to
``src/openzaak/conf/includes/local.py``. You can base this file on the
example file included in the same directory.

**Note:** You can run watch-tasks to compile `Sass`_ to CSS and `ECMA`_ to JS
using `gulp`_. By default this will compile the files if they change.

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
       $ gulp sass

3. Update the statics and database:

   .. code-block:: bash

       $ python src/manage.py collectstatic --link
       $ python src/manage.py migrate


Testsuite
---------

To run the test suite:

.. code-block:: bash

    $ python src/manage.py test openzaak

Configuration via environment variables
---------------------------------------

A number of common settings/configurations can be modified by setting
environment variables. You can persist these in your ``local.py`` settings
file or as part of the ``(post)activate`` of your virtualenv.

* ``SECRET_KEY``: the secret key to use. A default is set in ``dev.py``

* ``DB_NAME``: name of the database for the project. Defaults to ``open-zaak``.
* ``DB_USER``: username to connect to the database with. Defaults to ``open-zaak``.
* ``DB_PASSWORD``: password to use to connect to the database. Defaults to ``open-zaak``.
* ``DB_HOST``: database host. Defaults to ``localhost``
* ``DB_PORT``: database port. Defaults to ``5432``.

* ``SENTRY_DSN``: the DSN of the project in Sentry. If set, enabled Sentry SDK as
  logger and will send errors/logging to Sentry. If unset, Sentry SDK will be
  disabled.

Settings
========

All settings for the project can be found in
``src/openzaak/conf``.
The file ``includes/local.py`` overwrites settings from the base configuration.

Commands
========

Commands can be executed using:

.. code-block:: bash

    $ python src/manage.py <command>

There are no specific commands for the project. See
`Django framework commands`_ for all default commands, or type
``python src/manage.py --help``.

.. _Django framework commands: https://docs.djangoproject.com/en/dev/ref/django-admin/#available-commands
