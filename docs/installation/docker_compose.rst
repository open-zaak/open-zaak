.. _installation_docker_compose:

============================
Install using Docker Compose
============================

This installation is meant for people who want to just try out Open Zaak on
their own machine.

A `Docker Compose`_ file is available to get the app up and running in minutes.
It contains 'convenience' settings, which means that no additional
configuration is needed to run the app. Therefore, it should **not** be used
for anything other than testing. For example, it includes:

* A default ``SECRET_KEY`` environment variable
* A predefined database with the environment variable
  ``POSTGRES_HOST_AUTH_METHOD=trust``. This lets us connect to the database
  without using a password.
* Default admin credentials
* Runs against the latest version of Open Zaak, which may contain bugs.


Prerequisites
=============

You will only need Docker tooling and nothing more:

* `Docker Engine`_ (Desktop or Server, 18.09 or newer)
* `Docker Compose`_ (sometimes comes bundled with Docker Engine)

On Windows, we support WSL_ as a suitable a Linux-environment.

.. _`Docker Engine`: https://docs.docker.com/engine/install/
.. _`Docker Compose`: https://docs.docker.com/compose/install/
.. _`WSL`: https://docs.microsoft.com/en-us/windows/wsl/


Getting started
===============

1. Download the project as ZIP-file:

   .. code:: bash

      $ wget https://github.com/open-zaak/open-zaak/archive/refs/heads/main.zip -O main.zip
      $ unzip main.zip
      $ cd open-zaak-main

2. Start the docker containers with ``docker compose``. If you want to run the
   containers in the background, add the ``-d`` option to the command below:

   .. note:: the image build requires Docker BuildKit to be enabled - if this is not
      the case, you will see permission errors. You enable this by setting two environment
      variables:

      .. code:: bash

         export DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1

   .. code:: bash

      $ docker compose up

      [+] Running 5/5
       ⠿ Network open-zaak-main_default    Created      0.0s
       ⠿ Container open-zaak-main-db-1     Created      0.2s
       ⠿ Container open-zaak-main-redis-1  Created      0.2s
       ⠿ Container open-zaak-main-web-1    Created      0.1s
       ⠿ Container open-zaak-main-nginx-1  Created      0.1s

      ...

3. Navigate to http://127.0.0.1:8000/admin/ and log in with ``admin`` / ``admin``
   credentials.

4. To stop the containers, press *CTRL-C* or if you used the ``-d`` option:

   .. code:: bash

      $ docker compose stop

5. If you want to get newer versions, you need to ``pull`` because the
   ``docker-compose.yml`` contains no explicit versions:

   .. code:: bash

      $ docker compose pull
