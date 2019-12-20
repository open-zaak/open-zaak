============================
Apache Benchmark stress test
============================

Apache Bench is a good tool to measure raw HTTP performance. It is not
indicative for application performance, but rather aimed at testing your
infrastructure.

This document describes the configuration to run ``ab`` to make meaningful
comparisons and see which changes have which effect.

Running ``ab``
==============

.. code-block:: bash

    ab -n 1000 -c 100 https://test.openzaak.nl/zaken/api/v1/

The most interesting statistic is the number of requests per second, which you
want to be as high as possible.

Philosophy
==========

We run a total of 1000 requests to measure performance, using up to 100
concurrent users. Playing around with the concurrency level can reveal
hot spots or ideal numbers.

We test and API endpoint that has no IO and is inexpensive to generate. We
don't want to stress the application with queries or complicated template
rendering, which is why we pick an API root that generates very little JSON.

Note that if you are running the tests directly against other services, that
you may have to specify the ``Host`` header: ``-H 'Host: localhost'``, otherwise
Django will generate an HTTP 400 because of the ``InvalidHostHeader``, which
is very fast but not representative.

Also note that you want to run ``ab`` from a fast client machine. Aim for a
server in a different data center. We've seen cases where our client is limited
in requests per second because of a slow home network.

Parameters to vary
==================

* Traefik/Ingress: SSL termination happens here. We've seen Traefik CPU spikes
  with large private keys (4096 bits), and performance did improve a bit by
  changing to EC 256 bits at the cost of a worse SSL rating (A+ to A).

* Number of nginx replicas - more replicas can handle more traffic from Traefik

* Number of Open Zaak replicas - by default each container can handle 4
  concurrent requests (2 process \* 2 threads per process)

* Number of Open Zaak processes/threads in a container

* CPU/memory resource requests/limits in Kubernetes. Assigning more CPU/memory
  power will probably give better results. This applies for the Traefik, nginx
  and Open Zaak containers.

.. _ab: https://httpd.apache.org/docs/2.4/programs/ab.html
