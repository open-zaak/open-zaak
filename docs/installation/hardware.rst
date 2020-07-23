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

Based on functional :ref:`performance test scenario's<performance_scenarios>` and
requirements, we made a translation to technical performance requirements (requests per
second). We used the following numbers to make the translation:

1. Average number of requests per functional scenario: **7** (higher means more
   requests per second)
2. Average waiting time between functional scenario's: **5 minutes** (lower means more
   requests per second)

==================  ============================
Concurrent users    Expected requests per second
------------------  ----------------------------
  100               3
  250               6
  500               12
1.000               24
2.000               47
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

General recommendations
~~~~~~~~~~~~~~~~~~~~~~~

* Use a separate database server with roughly a third of the CPUs and memory as the
  main server. The database is usually the limiting factor.

Kubernetes recommendations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Preferably use 2 load balancer (like Traefik) replica's.
* Use as many replica's as available CPU's taking into account you need to have a few
  replica's for your load balancer, and possibly other services.
