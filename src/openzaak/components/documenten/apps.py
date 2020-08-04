# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DocumentenConfig(AppConfig):
    name = "openzaak.components.documenten"
    verbose_name = _("Documenten")

    def ready(self):
        # load the signal receivers
        from . import signals  # noqa

        # Initialize the viewset for Kanaal.get_usage
        from .api.viewsets import EnkelvoudigInformatieObjectViewSet  # noqa
