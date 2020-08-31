.. _installation_extra_logging:

=======
Logging
=======

Logging is a valuable tool to discover and debug issues happening when using Open Zaak.

Issues can be of different nature, and a different logging approach is suitable to
those. For example, the following types of events are logged in some form or another:

* unexpected application errors, as a result of programming mistakes (bugs) - these
  logs are technical in nature and should be accessible for Open Zaak developers.

* application server logs - startup and access logs of the server running Open Zaak.
  Useful to see if client requests actually reach the 'backend'

* webserver logs - Open Zaak uses a complex set-up to serve user-uploaded files
  securily. Things can go wrong here too.

* container logs - the docker container itself may have problems that need to be
  investigated.

This guide walks you through the various options on how to access and configure the logs.

Monitoring
==========

`Sentry`_ focuses on tracking down errors in software, i.e. the Open Zaak application.
We strongly recommend setting up this integration.

Open Zaak has support to itegrate with Sentry error monitoring. Whenever a bug occurs
in Open Zaak, the client will receive an error response **and** the technical details
of the error are sent to the Sentry project, with context.

.. note::
    Sentry integration makes sure to strip sensitive context from technical details.
    Passwords and/or other credentials are not sent to Sentry, if they happen to be in
    the request context.

For documentation on how to set up a project in Sentry, please refer to the official
`documentation`_ (make sure to follow the instructions for the platform Python > Django).

After setting up the project, you will receive a **DSN**, which is the URL to which
exceptions will be sent (e.g. https://e95a42137e6042c59d19376e566f027a@sentry.openzaak.nl/104).

The created Sentry project can be linked to Open Zaak by setting the environment
variable ``SENTRY_DSN`` equal to this DSN.

.. _`Sentry`: https://sentry.io/
.. _`documentation`: https://docs.sentry.io/guides/getting-started/


Viewing nginx logs
==================

Nginx is the webserver sitting between the client and the Open Zaak backend. It mostly
proxies requests to the backend, but it takes care of serving *Documenten API* files
after the authorization checks are performed.

.. _installation_logging_nginx_k8s:

On Kubernetes
-------------

Many Kubernetes providers provide a graphical interface to view logs, for example on
Google Cloud:

1. Navigate to your Kubernetes cluster
2. Via **Workloads**, find the deployment *nginx*
3. Find and click the **Container logs** link

Or, via the CLI tool ``kubectl``:

.. code-block:: shell

    # for convenience, set up the k8s namespace
    [user@host]$ kubectl config set-context --current --namespace=openzaak-test

    # fetch the logs
    [user@host]$ kubectl logs -l app.kubernetes.io/name=nginx

    # or for a single pod:
    [user@host]$ kubectl get pods
    NAME                        READY   STATUS    RESTARTS   AGE
    cache-79455b996-62llx       1/1     Running   0          68d
    nginx-8579d9dfbd-8dn5m      1/1     Running   0          7h3m
    nginx-8579d9dfbd-h4tc4      1/1     Running   0          7h3m
    openzaak-59df44f556-7znvg   1/1     Running   0          7h2m
    openzaak-59df44f556-gb4lq   1/1     Running   0          7h3m
    openzaak-59df44f556-nqtr2   1/1     Running   0          7h3m

    [user@host]$ kubectl logs --since=24h nginx-8579d9dfbd-8dn5m

On a VMWare appliance or single-server
--------------------------------------

On a single-server setup, nginx is not containerized and the log files can be found in
``/var/log/nginx``:

* ``/var/log/nginx/error.log`` contains errors encountered by nginx
* ``/var/log/nginx/access.log`` is the access log of all the client requests

Application server, application and container logs
==================================================

The application server, the application and the container itself write logs (together
they make up the 'backend').

1. When the container starts up, it performs some checks before it proceeds with the
   application server startup.
2. Then, the application server starts up and writes some status information.
3. Every request that is received by the application server is logged as well - this is
   the access log.
4. Finally, the application itself detects potential problematic situations or writes
   other informational messages to the logging output.

**All of these logs are logged to the container logs.**

Viewing the container logs on Kubernetes
----------------------------------------

As with the :ref:`nginx logs on Kubernetes<installation_logging_nginx_k8s>`, you can
make use of your provider's graphical interface if available.

Otherwise, you can use the CLI tool:

.. code-block:: shell

    # for convenience, set up the k8s namespace
    [user@host]$ kubectl config set-context --current --namespace=openzaak-test

    # fetch the logs
    [user@host]$ kubectl logs -l app.kubernetes.io/name=django

    # or for a single pod:
    [user@host]$ kubectl get pods
    NAME                        READY   STATUS    RESTARTS   AGE
    cache-79455b996-62llx       1/1     Running   0          68d
    nginx-8579d9dfbd-8dn5m      1/1     Running   0          7h3m
    nginx-8579d9dfbd-h4tc4      1/1     Running   0          7h3m
    openzaak-59df44f556-7znvg   1/1     Running   0          7h2m
    openzaak-59df44f556-gb4lq   1/1     Running   0          7h3m
    openzaak-59df44f556-nqtr2   1/1     Running   0          7h3m

    [user@host]$ kubectl logs --since=24h openzaak-59df44f556-gb4lq

On a VMWare appliance or single-server
--------------------------------------

Unfortunately, docker does not seem to be able to aggregate logs from different
containers. This means that if you are running multiple replicas of Open Zaak (which
is the default), you may have to dig around a bit before you find what you are looking
for.

To view the logs of a particular replica:

.. code-block:: shell

    # first replica
    [root@server]# docker logs openzaak-0

    # second replica
    [root@server]# docker logs openzaak-1

Check the `Docker documentation`_ for more information about logs in Docker.

.. _`Docker documentation`: https://docs.docker.com/engine/reference/commandline/logs/

.. _installation_logging_customize:

Customizing the log output
==========================

Logging to file instead
-----------------------

By default, we configure Open Zaak to log to stdout in containers by setting the
environment variable ``LOG_STDOUT=1``.

You may wish to log to files instead, by using persistent volumes. If you decide to do
this, then:

1. Make sure to mount the volume on ``/app/log`` - this is where log files are written
   to.
2. When multiple replicas are used, the volume must be ``ReadWriteMany`` on Kubernetes.
3. Set the environment variable ``LOG_STDOUT=0`` to fall back to file-based logging.

.. note::
    Log files are by default rotated - once a log file reaches 10MB, a new file is
    created and once 10 files exist, the oldest is deleted.

Logging infrastructure
----------------------

Various log-aggregation solutions exist in the industry, such as `ELK Stack`_,
`Grafana`_, `fluentd`_ and others. Consult their documentation on how to integrate them with Docker
and/or Kubernetes.

.. _ELK Stack: https://www.elastic.co/what-is/elk-stack
.. _Grafana: https://grafana.com/
.. _fluentd: https://www.fluentd.org/

Different needs?
----------------

Talk to us on `Github`_ if the current infrastructure does not fit your needs!

.. _Github: https://github.com/open-zaak/open-zaak/issues
