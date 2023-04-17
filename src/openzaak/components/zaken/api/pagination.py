# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.core.paginator import Paginator as DjangoPaginator

from rest_framework.pagination import PageNumberPagination


class ZaakPaginator(DjangoPaginator):
    def count(self):
        """
        ⚡ restricts values to PK to remove implicit join from SQL query
        """
        return self.object_list.values("pk").count()


class ZaakPagination(PageNumberPagination):
    django_paginator_class = ZaakPaginator
