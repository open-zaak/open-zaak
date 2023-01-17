.. _performance_notifications:

Notifications performance
=========================

Open Zaak sends notifications using `Celery`_ as a task queue.
Since sending notifications is asynchronous we use auto retry in case the tasks have failed.

Below we analyze the reliability and performance of sending notifications about
the creation of the zaak.


Sending notifications under burst load
--------------------------------------

We measure the notifications median time and failure rate under the increasing
amount of concurrent users.

**Test specifications:**

* 1 celery worker
* no waiting time between requests for 1 user
* all users send requests to create zaak (``POST /api/v1/zaken``)
* time under load is 1 minute

.. csv-table:: Notification performance results per users
   :header-rows: 1

    Users,Request Count,Requests/s,Failure Count,Median Response Time (ms),Notifications failure,Median Notification Time (ms)
    10,1430,24.183,0,390,0,88.572
    20,1479,25.034,0,740,0,83.922
    40,1429,24.189,0,1200,0,86.557

The results of the burst load test are promising. We have 0 failure rate both for zaak
creation and for sending of notifications about it.

.. _Celery: https://docs.celeryq.dev/en/stable/





