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

Architecture
============

The application is deployed as Docker containers, of which the images are
available on `docker hub`_. Traffic is routed to the server, where the web
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

Deployment
==========

Deployment is done with an Ansible playbook, performing the following steps:

1. Install and configure PostgreSQL database server
2. Install the Docker runtime
3. Install the SSL certificate with Letsencrypt
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

Create the ``secrets.yml`` file - you can find an example in
``vars/secrets.yml.example``. Generate a secret key using the
`django secret key generator`_ and put the value between single
quotes.

Configure the host by creating the ``hosts`` file from the example:

.. code-block:: shell

    (env) [user@laptop]$ cp hosts.example hosts

Edit the ``openzaak.gemeente.nl`` to point to your actual domain name. You must
make sure that the DNS entry for this domain points to the IP address of your
server.

.. warning:: It's important to use the correct domain name, as the SSL certificate
   will be generated for this domain and only this domain will be whitelisted
   by Open Zaak!

Running the deployment
----------------------

Execute the playbook by running:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-zaak.yml

If you have your secrets Ansible vault encrypted, make sure you have either:

* set the ``ANSIBLE_VAULT_PASSWORD_FILE`` environment variable or
* use the ``--ask-vault-pass`` flag.

If you need to override any deployment variables (see
:ref:`containers_config_params`), you can do this with the syntax
``-e "some_var=some_value other_var=other_value"``. For example:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-zaak.yml -e "certbot_create_if_missing=false"

.. note:: You can run the deployment multiple times, it will not affect the final
   outcome. If you decide to change configuration parameters, you do not have
   to start from scratch.

Environment configuration
-------------------------

After the initial deployment, some initial configuration is required. This
configuration is stored in the database and is only needed once.

**Create a superuser**

A superuser allows you to perform all administrative tasks.

Log in to the server:

.. code-block:: shell

    [user@laptop]$ ssh root@openzaak.gemeente.nl

Create the superuser (interactive on the shell). Note that the password you
type in will not be visible - not even with asterisks. This is normal.

.. code-block:: shell

    [root@openzaak.gemeente.nl]# docker exec -it openzaak-0 src/manage.py createsuperuser
    Gebruikersnaam: demo
    E-mailadres: admin@openzaak.gemeente.nl
    Password:
    Password (again):
    Superuser created successfully.

**Configure Open Zaak Admin**

1. Open ``https://openzaak.gemeente.nl/admin/`` in your favourite browser and log
   in with your superuser account.

2. Navigate to **Configuratie** > **Websites** and edit ``example.com``. Fill in
   your actual domain.

3. Navigate to **Configuratie** > **Notificatiescomponentconfiguratie** and
   specify the correct Notificaties API url.

4. Configure the credentials via **API autorisaties**.

.. _containers_config_params:

Configuration parameters
========================

At deployment time, you can configure a number of parts of the deployment by
overriding variables. You can override variables on the command line (using the
``-e "..."`` syntax) or by overriding them in ``vars/secrets.yml``.

.. note:: Tweaking configuration parameters is considered advanced usage.

Generic variables
-----------------

* ``certbot_admin_email``: e-mail address to use to accept the Letsencrypt
  terms and conditions.
* ``certbot_create_if_missing``: whether to use Letsencrypt to create an SSL
  certificate for your domain. Set to ``false`` if you want to use an existing
  certificate.

Open Zaak specific variables
----------------------------

The default values can be found in ``roles/openzaak/defaults/main.yml``.

* ``openzaak_db_port``: database port. If you are running multiple PostgreSQL versions
  on the same machine, you'll have to point to the correct port.
* ``openzaak_db_host``: specify the hostname if you're using a cloud database
  or a database on a different server.
* ``openzaak_db_name``: specify a different database name.
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

.. _docker hub: https://hub.docker.com/u/openzaak
.. _django secret key generator: https://miniwebtool.com/django-secret-key-generator/

Next steps
==========

To be able to work with Open Zaak, a couple of things have to be configured first,
see :ref:`installation_configuration` for more details.
