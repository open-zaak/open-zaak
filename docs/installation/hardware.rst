.. _installation_hardware:

Hardware requirements
=====================

Based on our initial :ref:`performance tests<performance_index>` in both a Kubernetes
environment and single machine setups, we can indicate some minimum system requirements
to reach a certain performance.

A Kubernetes setup will scale more easy while being a little more expensive.

Determine what you need
-----------------------

**Municipalities**

For municipality users, we made a small table of to quickly look up how many users we
expect to access the system concurrently based on the number of inhabitants. You can
also directly look at the concurrent users in the *performance* table below if this is
not applicable or you have a good idea of the number of concurrent users yourself.

==============  ============================
Inhabitants     Expected concurrent users
--------------  ----------------------------
   10.000         100
   50.000         250
  100.000         500
  500.000       1.000
1.000.000       2.000
==============  ============================

**Performance**

We made a translation to technical performance requirements (requests per
second). We used the following numbers to make the translation:

1. Average number of requests per functional scenario: **7** (higher means more
   requests per second)
2. Average waiting time between functional scenario's: **1 minute** (lower means more
   requests per second)

==================  ============================
Concurrent users    Expected requests per second
------------------  ----------------------------
  100               15
  250               30
  500               60
1.000               120
2.000               235
==================  ============================

The above number for requests per second depends greatly on the the actual usage of the
API. We used theoretical scenarios to give some indication, so it's best to use a
higher number when looking for the minimum system requirements below.

Minimum system requirements
---------------------------

* Platform: 64-bit
* Processor(s): 4 - 16 CPUs (see below) at 2.0 GHz
* RAM: 8 - 32 GB (see below)
* Hard disk space: 20 GB (excluding storage for documents)

Based on the number of requests per second you need, you can see what kind of hardware
you need to achieve this.

======================  ======  ==============
Requests per second     CPUs    Memory (GB)
----------------------  ------  --------------
 25                      4       8
 50                      6      12
100                     12      24
150                     14      28
200                     16      32
======================  ======  ==============

With these specifications you can run everything on a single machine or divided over
several instances.

Postgresql database minimum requirements
----------------------------------------

The performance of Open Zaak under load is very much dependant on the performance of the Postgresql database. The number of requests per second, the total number of cases and the number of cases per citizen/employee may affect the duration of the API calls. In order to avoid performance issues in production and aid in resolving performance issues we recommend to optimize the resources available and fine-tune the Postgresql with the help of `pgbench`. This built-in Postgresql tool gives an indication of the performance of the database setup. 

An example run using `pgbench`::

  pgbench (15.14 (Debian 15.14-0+deb12u1))
  scaling factor: 1
  query mode: simple
  number of clients: 16
  number of threads: 4
  maximum number of tries: 1
  duration: 60 s
  number of transactions actually processed: 65995
  number of failed transactions: 0 (0.000%)
  latency average = 14.543 ms
  latency stddev = 10.885 ms
  initial connection time = 23.771 ms
  tps = 1099.724563 (without initial connection time)

Using the default settings of pgbench, the following minimum `tps` is necessary for production setups:

=================  ====
Max cases per day  tps
-----------------  ----
100                200
1000               500
10000              1000
>10000+            1500
=================  ====



Kubernetes recommendations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Preferably use 2 load balancer (like Traefik) replica's.
* Use as many replica's as available CPU's taking into account you need to have a few
  replica's for your load balancer, and possibly other services.
