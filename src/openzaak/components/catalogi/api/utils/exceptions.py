from collections import OrderedDict

from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is not None:
        data = getattr(response, "data", {})
        request = context.get("request", object)

        response.data = OrderedDict(
            [
                ("type", exc.__class__.__name__),
                ("title", response.status_text),
                ("status", response.status_code),
                ("detail", data.get("detail", "")),
                ("instance", getattr(request, "path", "")),
            ]
        )

        if isinstance(exc, exceptions.ValidationError):
            response.data["invalid_params"] = [
                OrderedDict(
                    [
                        ("type", exc.__class__.__name__),
                        ("name", field_name),
                        ("reason", "; ".join(message)),
                    ]
                )
                for field_name, message in exc.detail.items()
            ]

    return response
