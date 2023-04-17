# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.conf import settings
from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property

from rest_framework.pagination import PageNumberPagination


class EnkelvoudigInformatieObjectPaginator(DjangoPaginator):
    @cached_property
    def count(self):
        """
        ⚡ restricts values to PK to remove implicit join from SQL query
        """
        if not settings.CMIS_ENABLED:
            # Objects in CMISQuerySet do not have `pk`s
            return self.object_list.values("pk").count()
        return super().count


class EnkelvoudigInformatieObjectPagination(PageNumberPagination):
    django_paginator_class = EnkelvoudigInformatieObjectPaginator
