from typing import Dict, List, Union
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models, transaction
from django.utils import timezone

from djangorestframework_camel_case.util import camelize
from notifications_api_common.api.serializers import NotificatieSerializer
from notifications_api_common.kanalen import Kanaal
from notifications_api_common.models import NotificationsConfig
from notifications_api_common.tasks import send_notification
from notifications_api_common.viewsets import NotificationMixin
from vng_api_common.utils import get_resource_for_path, get_viewset_for_path


class MultipleNotificationMixin(NotificationMixin):
    notification_fields = dict[str, dict[str, str]]

    def get_kanaal(self, field=None):
        try:
            return self.notification_fields[field]["notifications_kanaal"]
        except KeyError:
            raise ImproperlyConfigured(
                "'%s' should either include a `notification_variables` "
                "attribute, or override the `get_kanaal()` method."
                % self.__class__.__name__
            )

    def construct_message(
        self,
        data: dict,
        instance: models.Model = None,
        field: str = None,
    ) -> dict:
        """
        Construct the message to send to the notification component.

        Using the response data from the view/action, we introspect this data
        to send the appropriate response. By convention, every resource
        includes its own absolute url in the 'url' key - we can use this to
        look up the object it points to. By convention, relations use the name
        of the resource, so for sub-resources we can use this to get a
        reference back to the main resource.
        """
        kanaal = self.get_kanaal(field)
        assert isinstance(kanaal, Kanaal), "`kanaal` should be a `Kanaal` instance"

        model = self.notification_fields[field]["model"]

        if model is kanaal.main_resource:
            # look up the object in the database from its absolute URL
            resource_path = urlparse(data["url"]).path
            resource = instance or get_resource_for_path(resource_path)

            main_object = resource
            main_object_url = data["url"]
            main_object_data = data
        else:
            # lookup the main object from the URL
            main_object_url = self.get_notification_main_object_url(data, kanaal)
            main_object_path = urlparse(main_object_url).path
            main_object = get_resource_for_path(main_object_path)

            # get main_object data formatted by serializer
            view = get_viewset_for_path(main_object_path)
            serializer_class = view.get_serializer_class()
            serializer = serializer_class(
                main_object, context={"request": self.request}
            )
            main_object_data = serializer.data

        message_data = {
            "kanaal": kanaal.label,
            "hoofd_object": main_object_url,
            "resource": model._meta.model_name,
            "resource_url": data["url"],
            "actie": self.action,
            "aanmaakdatum": timezone.now(),
            # each channel knows which kenmerken it has, so delegate this
            "kenmerken": kanaal.get_kenmerken(
                main_object, main_object_data, request=getattr(self, "request", None)
            ),
        }

        # let the serializer & render machinery shape the data the way it
        # should be, suitable for JSON in/output
        serializer = NotificatieSerializer(instance=message_data)
        return camelize(serializer.data)

    def notify(
        self,
        status_code: int,
        data: Union[List, Dict],
        instance: models.Model = None,
        field: str = None,
    ) -> None:
        from notifications_api_common.viewsets import logger

        if settings.NOTIFICATIONS_DISABLED:
            return

        # do nothing unless we have a 'success' status code - early exit here
        if not 200 <= status_code < 300:
            logger.info(
                "Not notifying, status code '%s' does not represent success.",
                status_code,
            )
            return

        # build the content of the notification
        message = self.construct_message(data, instance=instance, field=field)

        # build the client from the singleton config.
        # This will raise an exception if the config is not complete unless
        # NOTIFICATIONS_GUARANTEE_DELIVERY is explicitly set to False
        client = NotificationsConfig.get_client()
        if client is None:
            msg = "Not notifying, Notifications API configuration is broken or absent."
            logger.warning(msg)
            if settings.NOTIFICATIONS_GUARANTEE_DELIVERY:
                raise RuntimeError(msg)
            return

        # We've performed all the work that can raise uncaught exceptions that we can
        # still put inside an atomic transaction block. Next, we schedule the actual
        # sending block, which allows failures that are logged. Any unexpected errors
        # here will still cause the transaction to be committed (in the default
        # behaviour), but the exception will be visible in the error monitoring (such
        # as Sentry).
        #
        # The 'send_notification' task is passed down to the task queue on transaction commit

        def _send():
            send_notification.delay(message)

        transaction.on_commit(_send)
