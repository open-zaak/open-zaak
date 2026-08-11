# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property

from rest_framework.pagination import PageNumberPagination
from vng_api_common.pagination import DynamicPageSizeMixin


class ExactPaginator(DjangoPaginator):
    @cached_property
    def count(self):
        """
        ⚡ restricts values to PK to remove implicit join from SQL query
        """
        return self.object_list.values("pk").count()


class ExactPagination(DynamicPageSizeMixin, PageNumberPagination):
    django_paginator_class = ExactPaginator
