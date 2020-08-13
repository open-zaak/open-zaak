.. _deployment_containers:

============================
Deploying on a single server
============================

Open Zaak can be deployed on a single machine - either a dedicated server (DDS)
or virtual private server (VPS). The required hardware can be rented from a
hosting provider or be provided in your environment. Please see
:ref:`installation_hardware` to determine the hardware requirements.

This documentation describes the architecture, prerequisites and how to deploy
Open Zaak on a server. Additionally, it documents the possible configuration
options.

.. note:: The default settings allow Open Zaak to be deployed to the same
   machine as Open Notificaties.

Architecture
============

The application is deployed as Docker containers, of which the images are
available on `Docker hub`_. Traffic is routed to the server, where the web
server (nginx) handles SSL termination and proxies the requests to the
application containers.

Data is stored in a PostgreSQL database. By default, the database is installed
on the same machine (running on the host), but you can make use of a hosted
database (Google Cloud, AWS, Azure...). See the :ref:`containers_config_params`
for more information.

Prerequisites
=============

Before you can deploy, you need:

A server
--------

Ensure you have a server with ``root`` privileges. We assume you can directly
ssh to the machine as ``root`` user. If that's not the case, a user with
``sudo`` will also work. Python 3 must be available on the server. Debian 9/10
are officially supported operating systems, though it is likely the
installation also works on Ubuntu. CentOS/RedHat *might* work.

.. note:: Make sure there is enough space in ``/var/lib/docker``. You need at 
   least 8 GB to download all Docker containers. We recommend placing the Docker
   folder wherever you also want to store your documents that are uploaded via
   the Documenten API.

.. _deployment_containers_tooling:

A copy of the deployment configuration
--------------------------------------

You can either clone the https://github.com/open-zaak/open-zaak repository,
or download and extract the latest ZIP:
https://github.com/open-zaak/open-zaak/archive/master.zip

Python and a Python virtualenv
------------------------------

You will need to have at least Python 3.5 installed on your system. In the
examples, we assume you have Python 3.6.

Create a virtualenv with:

.. code-block:: shell

    [user@laptop]$ python3.6 -m venv env/
    [user@laptop]$ source env/bin/activate

Make sure to install the deployment tooling. In your virtualenv, install the
dependencies:

.. code-block:: shell

    (env) [user@laptop]$ pip install -r deployment/requirements.txt
    (env) [user@laptop]$ cd deployment/single-server
    (env) [user@laptop]$ ansible-galaxy collection install -r requirements.yml
    (env) [user@laptop]$ ansible-galaxy role install -r requirements.yml

Deployment
==========

Deployment is done with an Ansible playbook, performing the following steps:

1. Install and configure PostgreSQL database server
2. Install the Docker runtime
3. Install the SSL certificate with Let's Encrypt
4. Setup Open Zaak with Docker
5. Install and configure nginx as reverse proxy

Initial steps
-------------

Make sure the virtualenv is activated:

.. code-block:: shell

    [user@laptop]$ source env/bin/activate

Navigate to the correct deployment directory:

.. code-block:: shell

    (env) [user@laptop]$ cd deployment/single-server

Create the ``vars/open-zaak.yml`` file - you can find an example in
``vars/open-zaak.yml.example``. Generate a secret key using the
`Django secret key generator`_ and put the value between single
quotes.

Configure the host by creating the ``hosts`` file from the example:

.. code-block:: shell

    (env) [user@laptop]$ cp hosts.example hosts

In the `hosts` file, edit the ``open-zaak.gemeente.nl`` to point to your actual 
domain name. You must make sure that the DNS entry for this domain points to the 
IP address of your server.

.. warning:: It's important to use the correct domain name, as the SSL certificate
   will be generated for this domain and only this domain will be whitelisted
   by Open Zaak! If you are using a private DNS name, then no SSL certificate
   can be created via Letsencrypt - make sure to disable it by setting
   ``certbot_create_if_missing=false`` or ``openzaak_ssl=false`` if you don't
   plan on using HTTPS at all.

.. _deployment_containers_playbook:

Running the deployment
----------------------

Execute the playbook by running:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-zaak.yml

.. hint::

   * If you have your secrets Ansible vault encrypted, make sure you have either:

     * set the ``ANSIBLE_VAULT_PASSWORD_FILE`` environment variable, or
     * pass ``--ask-vault-pass`` flag to ``ansible-playbook``.

   * If you need to override any deployment variables (see
     :ref:`containers_config_params`), you can pass variables to
     ``ansible-playbook`` using the syntax:
     ``--extra-vars "some_var=some_value other_var=other_value"``.

   * If you want to run the deployment from the same machine as where it will
     run (ie. install to itself), you can pass ``--connection local`` to
     ``ansible-playbook``.

   * If you cannot connect as ``root`` to the target machine, you can pass
     ``--user <user> --become --become-method=sudo --ask-become-pass`` which
     will connect as user ``<user>`` that needs ``sudo``-rights on the target
     machine to install the requirements.

A full example might look like this:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-zaak.yml \
        --user admin
        --inventory my-hosts \  # Use inventory file ``my-hosts`` instead of ``hosts``.
        --limit open-zaak.gemeente.nl \  # Only pick open-zaak.gemeente.nl from the inventory file.
        --extra-vars "openzaak_ssl=false openzaak_db_name=open-zaak-test openzaak_db_username=open-zaak-test" \
        --connection local \
        --become \
        --become-method=sudo \
        --ask-become-pass

.. note:: You can run the deployment multiple times, it will not affect the final
   outcome. If you decide to change configuration parameters, you do not have
   to start from scratch.

**Changing environment variables**

The Open Zaak configuration is templated out to ``/home/openzaak/.env`` on the host
machine. It's possible to modify environment variables here, but doing so will not
become effective immediately - you need to restart the containers:

.. code-block:: shell

    [root@host]# docker restart openzaak-0 openzaak-1 openzaak-2

Make sure to do this for every replica - you can see what's running with ``docker ps``.

.. warning:: If you modify the ``.env`` file and then apply the Ansible playbook again,
    this will overwrite your changes!

Environment configuration
-------------------------

After the initial deployment, some initial configuration is required. This
configuration is stored in the database and is only needed once.

**Create a superuser**

A superuser allows you to perform all administrative tasks.

1. Log in to the server:

   .. code-block:: shell

       [user@laptop]$ ssh root@open-zaak.gemeente.nl

2. Create the superuser (interactive on the shell). Note that the password you
   type in will not be visible - not even with asterisks. This is normal.

   .. code-block:: shell

       [root@open-zaak.gemeente.nl]# docker exec -it openzaak-0 src/manage.py createsuperuser
       Gebruikersnaam: demo
       E-mailadres: admin@open-zaak.gemeente.nl
       Password:
       Password (again):
       Superuser created successfully.

**Configure Open Zaak Admin**

See the :ref:`installation_configuration` on how to configure Open Zaak
post-installation.

.. _containers_config_params:

Configuration parameters
========================

At deployment time, you can configure a number of parts of the deployment by
overriding variables. You can override variables on the command line (using the
``-e "..."`` syntax) or by overriding them in ``vars/secrets.yml``.

.. note:: Tweaking configuration parameters is considered advanced usage.

Generic variables
-----------------

* ``certbot_admin_email``: e-mail address to use to accept the Let's Encrypt
  terms and conditions.
* ``openzaak_ssl``: whether to use Let's Encrypt to create an SSL
  certificate for your domain. Set to ``false`` if you want to use an existing
  certificate.

Open Zaak specific variables
----------------------------

The default values can be found in in the `Ansible role`_.

* ``openzaak_db_port``: database port. If you are running multiple PostgreSQL versions
  on the same machine, you'll have to point to the correct port.
* ``openzaak_db_host``: specify the hostname if you're using a cloud database
  or a database on a different server.
* ``openzaak_db_name``: specify a different database name.
* ``openzaak_db_username``: specify a different database username.
* ``openzaak_db_password``: specify a different database username.
* ``openzaak_secret_key``: A Django secret key. Used for cryptographic
  operations - this may NOT leak, ever. If it does leak, change it.

**Scaling**

The ``openzaak_replicas`` variable controls scaling on backend services. If
your hardware allows it, you can create more replicas. By default, 3 replicas
are running.

The format of each replica is:

.. code-block:: yaml

    name: openzaak-i
    port: 800i

The port number must be available on the host - i.e. you may not have other
services already listening on that port.

.. _Docker hub: https://hub.docker.com/u/openzaak
.. _Django secret key generator: https://miniwebtool.com/django-secret-key-generator/
.. _Ansible role: https://github.com/open-zaak/ansible-collection/blob/master/roles/open_zaak_docker/defaults/main.yml

Next steps
==========

You may want to :ref:`customize the logging setup<installation_logging_customize>`. The
default setup should be sufficient to get started though.

To be able to work with Open Zaak, a couple of things have to be configured first,
see :ref:`installation_configuration` for more details.

.. _deployment_containers_updating:

Updating an Open Zaak installation
==================================

Make sure you have the deployment tooling installed - see
:ref:`the installation steps<deployment_containers_tooling>` for more details.

If you have an existing environment (from the installation), make sure to update it:

.. code-block:: shell

    # fetch the updates from Github
    [user@host]$ git fetch origin

    # checkout the tag of the version you wish to update to, e.g. 1.0.0
    [user@host]$ git checkout X.Y.z

    # activate the virtualenv
    [user@host]$ source env/bin/activate

    # ensure all (correct versions of the) dependencies are installed
    (env) [user@host]$ pip install -r requirements.txt
    (env) [user@host]$ ansible-galaxy install -r requirements.yml

Open Zaak deployment code defines variables to specify the Docker image tag to use. This
is synchronized with the git tag you're checking out.

.. warning::
    Make sure you are aware of possible breaking changes or manual interventions by
    reading the :ref:`development_changelog`!

Next, to perform the upgrade, you run the ``open-zaak.yml`` playbook just like with the
installation in :ref:`deployment_containers_playbook`:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-zaak.yml

.. note::
    This will instruct the docker containers to restart using a new image. You may
    notice some brief downtime (order of seconds to minutes) while the new image is
    being downloaded and containers are being restarted.
