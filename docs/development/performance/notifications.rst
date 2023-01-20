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


Automatic retry for notifications
---------------------------------

Sending notifications can be done with automatic retry, i.e. if the notification task was failed it
will be autoretried the configured number of times. We measure how autoretry works with increasing downtime
of the notification service.

**Test specifications:**

* 1 celery worker
* 10 concurrent users
* no waiting time between requests for 1 user
* all users send requests to create zaak (``POST /api/v1/zaken``)
* requests are send during 1 min
* auto retry settings are default (5 maximum attempts per task)

.. csv-table:: Notification autoretries per downtime
   :header-rows: 1

    Notification downtime (s),Request Count,Failure Count,Notifications failed,Notifications retried,Notifications processed
    10,1486,0,0,919,2114
    60,1478,0,0,3729,5195
    300,1509,0,1276,6380,7908

According to the result if the notification server is down for less than 1 min, then all notifications
would be eventually send. If it's expected that the notification service is down for longer time
the autoretry configuration should be adjusted in the admin.