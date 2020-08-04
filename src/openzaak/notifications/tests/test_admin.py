# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Test that notifications can be send again through the admin.
"""
from typing import List

from django.urls import reverse
from django.utils import timezone

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.notifications.tests.mixins import NotificationServiceMixin

from ..models import FailedNotification
from . import mock_notification_send, mock_oas_get
from .factories import FailedNotificationFactory


@requests_mock.Mocker()
class FailedNotificationAdminTests(NotificationServiceMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

        cls.url = reverse("admin:notifications_log_failednotification_changelist")

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def _resend_all(self, notifs: List[FailedNotification]):
        response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-form"]
        form["action"].select("resend_notifications")

        for i, notif in enumerate(notifs):
            form.set("_selected_action", index=i, value=notif.pk)

        response = form.submit("index")
        self.assertEqual(response.status_code, 302)

    def test_resend_ok(self, m):
        mock_oas_get(m)
        mock_notification_send(m)
        notifs = FailedNotificationFactory.create_batch(3)

        self._resend_all(notifs)

        qs = FailedNotification.objects.filter(retried_at__isnull=True)
        self.assertFalse(qs.exists())

    def test_skip_already_retried(self, m):
        mock_oas_get(m)
        mock_notification_send(m)

        fn1 = FailedNotificationFactory.create(retried_at=None)
        fn2 = FailedNotificationFactory.create(retried_at=timezone.now())

        self._resend_all([fn1, fn2])

        requests = [req for req in m.request_history if req.method == "POST"]
        self.assertEqual(len(requests), 1)

    def test_no_crash_on_expected_failure(self, m):
        """
        Test that one resend failing does not prevent others from being sent.
        """
        mock_oas_get(m)

        calls = {"counter": 0}

        def json_callback(request, context):
            calls["counter"] += 1
            if calls["counter"] == 1:
                context.status_code = 403
            return {"dummy": "response"}

        mock_notification_send(m, json=json_callback)

        notifs = FailedNotificationFactory.create_batch(2)

        self._resend_all(notifs)

        notifs[0].refresh_from_db()
        self.assertIsNotNone(notifs[0].retried_at)

        notifs[1].refresh_from_db()
        self.assertIsNotNone(notifs[1].retried_at)

        # failed notifications must be logged again
        qs = FailedNotification.objects.filter(retried_at__isnull=True)
        self.assertEqual(qs.count(), 1)

    def test_no_crash_on_unexpected_failure(self, m):
        """
        Test that one resend failing does not prevent others from being sent.
        """
        mock_oas_get(m)

        calls = {"counter": 0}

        def json_callback(request, context):
            calls["counter"] += 1
            if calls["counter"] == 1:
                raise Exception("it broke")
            return {"dummy": "response"}

        mock_notification_send(m, json=json_callback)

        notifs = FailedNotificationFactory.create_batch(2)

        self._resend_all(notifs)

        notifs[0].refresh_from_db()
        self.assertIsNotNone(notifs[0].retried_at)

        notifs[1].refresh_from_db()
        self.assertIsNotNone(notifs[1].retried_at)

        qs = FailedNotification.objects.filter(retried_at__isnull=True)
        self.assertFalse(qs.exists())
