.. _deployment_linux:

==========================
Linux deployment reference
==========================

The Linux deployment reference serves as an example on the parts making up an
Open Zaak installation. Parts of this are handled by distributing build
artifacts as Docker container images. Some of the concepts from this reference
are handled in the image build, others have become completely obsolete.

For actual production deployment, we recommend you to look at either:

* :ref:`deployment_containers`
* :ref:`deployment_kubernetes`

If you want to tinker with the various parts, please continue reading :-)

Prerequisites
=============

You will need a Linux server with privileged access, since we'll be modifying
webserver configuration files. You will need a Linux distribution that offers
Python 3.7 or has the means to install Python 3.7. The 'server' concept here
can be a development machine.

We test on, and therefore recommend, Debian or Ubuntu LTS versions. In theory,
the instructions apply for RedHat and CentOS as well, though package names
and configuration directories are often different from Debian-based systems.

Note that some requirements can be filled in by hosted/remote services. If you
make use of those instead of running them on the same machine, you may get a
little bit of network overhead and thus a small amount of performance loss.

Hardware requirements
---------------------

See the :ref:`hardware requirements guide<installation_hardware>`.

Software requirements
---------------------

At least the following software must be present on the server system:

* Python 3.7 (with virtualenv, which is present by default).
* A PostgreSQL database server (at least version 10) with PostGIS enabled. You
  can make use of a remote database or run it on the same server.
* Redis as message broker and cache. May be on the same machine, or a remote
  service.
* nGinx webserver
* Server packages

    * ``libpq-dev``
    * ``postgresql-client``
    * ``libgdal20``
    * ``libgeos-c1v5``
    * ``libproj12``

Other
-----

* An SSL-certificate for the domain that you'll be hosting the deployment on
  (strongly recommended!).

Server preparations
===================

Firewall
--------

Firewalls must be configured such that the following traffic is allowed:

**Outgoing HTTP to Sentry**

If the application is configured to report errors to Sentry, the firewall must
allow outgoing HTTPS traffic to this domain.

**Database**

If you're making use of a remote database, then outgoing TCP traffic to the
database host and port (default ``5432``) is required.

If the database is hosted on the same machine, then either traffic on
``localhost`` to port ``5432`` is required, or you can make use of the database
socket (typically in ``/var/run/postgresql/.s.PGSQL.5432``).

**Redis**

If you're making use of a remote Redis cluster, then outgoing TCP traffic to
the redis host and port (default ``6379``) is required.

For a Redis cluster hosted on the same system, traffic to ``localhost:6379``
must be permitted.

.. _linux-database-preparation:

Database
--------

.. note:: If you are using a remote database, you can skip over this section.
    Make sure to have the hostname, port, database name, database user and
    database password at hand for the configuration later.

We recommend creating a database user with the minimal privileges. For the
username, we will use ``openzaak`` in the examples. As for the database name,
we will use ``production`` as example.

To perform these actions, you need a privileged database user with permissions
to create users, databases and extensions. Usually the ``postgres`` user is
superuser.

Become the ``postgres`` user:

.. code-block:: console

    [root@linux ~]# su postgres

Create the application database user:

.. code-block:: console

    [postgres@linux ~]$ createuser openzaak --pwprompt
    Enter password for new role:
    Enter it again:

Create the application database:

.. code-block:: console

    [postgres@linux ~]$ createdb production --owner openzaak

Initialize the database with the required extensions:

.. code-block:: console

    [postgres@linux ~]$ psql production -c "CREATE EXTENSION postgis;"

Preparing the webserver
-----------------------

Assuming a default nginx layout (in ``/etc/nginx``)::

    .
    ├── conf.d
    ├── fastcgi.conf
    ├── fastcgi_params
    ├── koi-utf
    ├── koi-win
    ├── mime.types
    ├── modules-available
    ├── modules-enabled
    ├── nginx.conf
    ├── proxy_params
    ├── scgi_params
    ├── sites-available
    ├── sites-enabled
    ├── snippets
    ├── uwsgi_params
    └── win-utf

**Ensure a strong enough DH key is present**

If there is no ``/etc/ssl/certs/dhparam.pem``, create one:

.. code-block:: console

    [root@linux ~]# openssl dhparam -out /etc/ssl/certs/dhparam.pem 4096

Note that this may take a while.

**Prepare your SSL private key and public certificate**

Put your SSL private key in ``/etc/ssl/sites/private.key`` and the public
certificate chain in ``/etc/ssl/sites/public.cert``.

.. note:: The public certificate must contain the full chain! See the
    `ssl certificate chains documentation`_ for more information.

**Define virtualhost**

Create the virtual host config in ``/etc/nginx/sites-available/production``:

.. literalinclude:: code/nginx-vhost.conf
    :language: nginx
    :linenos:
    :emphasize-lines: 9,17

Make sure to enter the correct domain names in the ``server`` blocks.

.. todo:: Enable TLS 1.3 in nginx

Preparing the application
-------------------------

**Fetching the application code**

You can get the source code by using a git-clone of the repository, or by
downloading it manually from
``https://github.com/open-zaak/open-zaak/archive/master.zip``.

Install the code in the ``/srv/sites/production`` directory, the directory
structure should look like::

    .
    ├── bin
    ├── build
    ├── docker-compose.yml
    ├── Dockerfile
    ├── docs
    ├── Gulpfile.js
    ├── LICENSE.md
    ├── log
    ├── package.json
    ├── package-lock.json
    ├── README.rst
    ├── requirements
    ├── setup.cfg
    └── src

Make sure the ``nginx`` user has write permissions on ``log/nginx``.

**Enable the nginx virtualhost**

A virtualhost is enabled by symlinking the configuration. After that, verify
the nginx config and if everything is fine, you can reload the service.

.. code-block:: console

    [root@linux ~]# ln -s /etc/nginx/sites-enabled/production /etc/nginx/sites-available/production
    [root@linux ~]# nginx -t
    [root@linux ~]# systemctl reload nginx

**Installing dependencies**

It's best practice to create a virtual environment to isolate dependencies:

.. code-block:: console

    [app@linux ~]$ cd /srv/sites/production
    [app@linux production]$ python3.7 -m venv env
    [app@linux production]$ source env/bin/activate
    [app@linux production](env)$ pip install -r requirements/production.txt

**Creating the .env-file**

A ``.env`` file contains the credentials to the database, redis server... and
other configuration aspects.

Create the file ``/srv/sites/production/.env``, with at least the following
content:

.. literalinclude:: code/env

You can now test if the basic install was done correctly:

.. code-block:: console

    [app@linux production](env)$ python src/manage.py check
    System check identified no issues (1 silenced).

**Syncing the database**

Run:

.. code-block:: console

    [app@linux production](env)$ python src/manage.py migrate

to initialize/update the database schema.

**Creating an administrative user**

Run

.. code-block:: console

    [app@linux production](env)$ python src/manage.py createsuperuser

and follow the prompts. You can log in with this user on
``https://open-zaak.gemeente.nl/admin/`` after completing the deployment.

**Running the backend server**

To avoid extra dependencies, we recommend setting up a `systemd`_ service.

Create ``/etc/systemd/system/production.service``:

.. literalinclude:: code/openzaak.service
    :language: ini

and ``/etc/systemd/system/production.socket``:

.. literalinclude:: code/openzaak.socket
    :language: ini

.. _ssl certificate chains documentation: http://nginx.org/en/docs/http/configuring_https_servers.html#chains
.. _systemd: https://en.wikipedia.org/wiki/Systemd
