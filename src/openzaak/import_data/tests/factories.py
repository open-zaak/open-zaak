# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from typing import Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse

import factory
import factory.fuzzy

from openzaak.components.catalogi.models.informatieobjecttype import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories.informatie_objecten import (
    InformatieObjectTypeFactory,
)
from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices


class ImportFactory(factory.django.DjangoModelFactory):
    import_type = factory.fuzzy.FuzzyChoice(ImportTypeChoices.values)
    status = ImportStatusChoices.pending

    import_file = factory.django.FileField(
        filename=factory.Sequence(lambda n: f"import-{n}.csv")
    )
    report_file = factory.django.FileField(
        filename=factory.Sequence(lambda n: f"report-{n}.csv")
    )

    class Meta:
        model = Import


def get_informatieobjecttype_url(
    instance: Optional[InformatieObjectType] = None,
) -> str:
    if not instance:
        instance = InformatieObjectType.objects.first() or InformatieObjectTypeFactory()

    site = Site.objects.get()

    base_url = f"https://{site.domain}"
    instance_url = reverse(
        "informatieobjecttype-detail",
        kwargs=dict(
            uuid=instance.uuid,
            version=settings.REST_FRAMEWORK["DEFAULT_VERSION"],
        ),
    )

    return f"{base_url}{instance_url}"
