# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.admin.widgets import ForeignKeyRawIdWidget, ManyToManyRawIdWidget


class RawIdWidgetMixin:
    def __init__(self, *args, **kwargs):
        self.catalogus_pk = kwargs.pop("catalogus_pk")
        super().__init__(*args, **kwargs)

    def url_parameters(self):
        params = super().url_parameters()
        if self.catalogus_pk:
            params["catalogus__exact"] = self.catalogus_pk
        return params


class CatalogusFilterM2MRawIdWidget(RawIdWidgetMixin, ManyToManyRawIdWidget):
    pass


class CatalogusFilterFKRawIdWidget(RawIdWidgetMixin, ForeignKeyRawIdWidget):
    pass
