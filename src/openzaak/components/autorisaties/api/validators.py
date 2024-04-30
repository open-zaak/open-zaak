# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import List

from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import ValidationError
from vng_api_common.authorizations.models import Applicatie


class UniqueClientIDValidator:
    code = "clientId-exists"
    message = _(
        "The clientID(s) {client_id} are already used in application(s) {app_id}"
    )
    requires_context = True

    def __call__(self, value: List[str], serializer_field):
        instance = getattr(serializer_field.parent, "instance", None)
        qs = Applicatie.objects.all()

        if instance:
            qs = qs.exclude(id=instance.id)

        existing = qs.filter(client_ids__overlap=value).values_list(
            "uuid", "client_ids"
        )
        if existing:
            client_ids = set()
            for _existing in existing:
                client_ids = client_ids.union(_existing[1])

            raise ValidationError(
                self.message.format(
                    client_id=", ".join(client_ids.intersection(set(value))),
                    app_id=", ".join([str(_existing[0]) for _existing in existing]),
                ),
                code=self.code,
            )
