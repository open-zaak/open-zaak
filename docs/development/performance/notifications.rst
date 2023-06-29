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
* 3 processes for the worker
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
publishing task has failed, it will automatically be scheduled/tried again until the maximum
retry limit has been reached.

Autoretry explanation and configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Retry behaviour is implemented using binary exponential backoff with a delay factor,
the formula to calculate the time to wait until the next retry is as follows:

.. math::

    t = \text{backoff_factor} * 2^c

where `c` is the number of retries that have been performed already.

In **Configuratie > Notificatiescomponentconfiguratie** admin page the autoretry settings
can be configured:

* **Notification delivery max retries**: the maximum number of retries the task queue
  will do if sending a notification failed. Default is ``5``.
* **Notification delivery retry backoff**: a boolean or a number. If this option is set to
  ``True``, autoretries will be delayed following the rules of binary exponential backoff. If
  this option is set to a number, it is used as a delay factor. Default is ``3``.
* **Notification delivery retry backoff max**: an integer, specifying number of seconds.
  If ``Notification delivery retry backoff`` is enabled, this option will set a maximum
  delay in seconds between task autoretries. Default is ``48`` seconds.

With the assumption that the requests are done immediately we can model the notification
tasks schedule with the default configurations:

1. At 0s the request to create a zaak is made, the notification task is scheduled, picked up
   by worker and failed
2. At 3s with 3s delay the first retry happens (``2^0`` * ``Notification delivery retry backoff``)
3. At 9s with 6s delay - the second retry (``2^1`` * ``Notification delivery retry backoff``)
4. At 21s with 12s delay - the third retry
5. At 45s with 24s delay - the fourth retry
6. At 1m33s with 48s delay - the fifth retry, which is the last one.

So if the Notification API is up after 1 min of downtime the default configuration can handle it
automatically.

Autoretry test with default configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this scenario, we measure how autoretry behaves with increasing downtime durations of
the notification service and with the default autoretry configuration.

**Test specifications:**

* 1 celery worker
* 3 processes for the worker
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

* ``Notifications retried`` includes all notifications that were automatically retried.
  The minimum number equals the number of failed notifications. If all notifications are eventually failed
  ``Notifications retried`` = ``Notifications failed`` * ``maximum retries per task``.
* ``Notifications processed`` includes failed, retried and succeeded notifications.

According to the result if the notification server is down for less than 1 min, then all notifications
would be eventually send. If it's expected that the notification service is down for longer time
the autoretry configuration should be adjusted in the admin.

Autoretry test with adjusted configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the last case in the test run, when the notification server was down for 300 seconds,
all notifications have failed. Let's change the autoretry configuration, so the notifications
will be retrying during 5 minutes:

* **Notification delivery max retries** is changed to ``7``.
* **Notification delivery retry backoff max** is changed to ``192``.

With this configuration we expect the following task schedule:

7. At 189s with 96s delay - the 6th retry
8. At 381s with 192s delay - the 7th retry, which is now the last one.

**Test specifications:**

* 1 celery worker
* 3 processes for the worker
* 10 concurrent users
* no waiting time between requests for 1 user
* all users send requests to create zaak (``POST /api/v1/zaken``)
* requests are sent for a total duration of 1 min
* auto retry settings: ``7``

.. csv-table:: Notification autoretries per downtime
   :header-rows: 1

    Notification downtime (s),Request Count,Failure Count,Notifications failed,Notifications retried,Notifications processed
    10,1328,0,0,639,2002
    60,1335,0,0,3846,5209
    300,1262,0,0,7427,8717
    600,1393,0,1181,8267,9687

The adjusted autoretry configuration resulted in 0 failed notifications for 5 min downtime with the tradeoff of
the increased amount of the retried ones. However the adjusted settings were not efficient for the 10 min downtime.
Therefore we advice to take into account the statistics of server downtimes before adjusting autoretry settings.