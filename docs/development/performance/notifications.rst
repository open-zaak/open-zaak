.. _performance_notifications:

Notifications performance
=========================

Open Zaak sends notifications using `Celery`_ as an asynchronous task queue. Notification delivery
failure to the Notifications API/service may happen, which is why we leverage "autoretry" for
these failed tasks.

The reliability and performance of sending notifications was analyzed and the results are reported
below. In this test case, we observed the behaviour of notifications triggered by "case create" 
events.


Sending notifications under burst load
--------------------------------------

We measure the notifications median time and failure rate under an increasing
amount of concurrent users. The goal is to observe the reliability of notification
delivery and delay between notification scheduling and it actually arriving at the
Notifications API.

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

The data suggests no reliability issues, even with only a single Celery worker, as the failure
rates are 0 for both the API operation and notification delivery.

Note that the worker containers can scale horizontally and we recommend deploying at 
least two worker containers, ideally distributed over different hardware instances for 
high-available set-ups.

.. _Celery: https://docs.celeryq.dev/en/stable/


Automatic retry for notifications
---------------------------------

By default, sending notifications has automatic retry behaviour, i.e. if the notification
publishing task hasfailed, it will automatically be scheduled/tried again until the maximum
retry limit has been reached.

In this scenario, we measure how autoretry behaves with increasing downtime durations of 
the notification service.

**Test specifications:**

* 1 celery worker
* 10 concurrent users
* no waiting time between requests for 1 user
* all users send requests to create zaak (``POST /api/v1/zaken``)
* requests are sent for a total duration of 1 min
* auto retry settings: default (5 maximum attempts per task)

.. csv-table:: Notification autoretries per downtime
   :header-rows: 1

    Notification downtime (s),Request Count,Failure Count,Notifications failed,Notifications retried,Notifications processed
    10,1486,0,0,919,2114
    60,1478,0,0,3729,5195
    300,1509,0,1276,6380,7908

According to the result if the notification server is down for less than 1 min, then all notifications
would be eventually send. If it's expected that the notification service is down for longer time
the autoretry configuration should be adjusted in the admin.