# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from collections import OrderedDict

from django.conf import settings
from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property

from rest_framework.pagination import PageNumberPagination, _positive_int
from rest_framework.response import Response
from vng_api_common.pagination import DynamicPageSizeMixin

from .help_text import mark_experimental


class ExactPaginator(DjangoPaginator):
    @cached_property
    def count(self):
        """
        ⚡ restricts values to PK to remove implicit join from SQL query
        """
        return self.object_list.values("pk").count()


class ExactPagination(DynamicPageSizeMixin, PageNumberPagination):
    django_paginator_class = ExactPaginator


class FuzzyPaginator(DjangoPaginator):
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True):
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)
        self.page_number = None

    def page(self, number):
        # Pass the page number to the paginator, to calculate the limit in count
        self.page_number = number

        return super().page(number)

    @cached_property
    def count(self):
        offset = (_positive_int(self.page_number) - 1) * self.per_page
        return self.object_list.values("pk")[
            : offset + settings.FUZZY_PAGINATION_COUNT_LIMIT
        ].count()


class FuzzyPagination(DynamicPageSizeMixin, PageNumberPagination):
    django_paginator_class = FuzzyPaginator

    def get_paginated_response(self, data):
        response_data = [
            ("count", self.page.paginator.count),
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("results", data),
        ]

        count_exact = self.page.paginator.count % self.page_size != 0
        response_data.insert(3, ("count_exact", count_exact))

        return Response(OrderedDict(response_data))

    def get_paginated_response_schema(self, schema):
        paginated_schema = super().get_paginated_response_schema(schema)
        paginated_schema["properties"]["countExact"] = {
            "type": "boolean",
            "description": mark_experimental(
                "Geeft aan of de `count` exact is, of dat deze wegens "
                "performance doeleinden niet exact berekend is."
            ),
        }

        return paginated_schema


class CursorPageNumberPagination(DynamicPageSizeMixin, PageNumberPagination):
    page_size = 100  # Set a fixed page size

    def paginate_queryset(self, queryset, request, view=None):

        # TODO implement ordering based on params
        ordering_field = "identificatie_ptr_id"
        # Get the requested page number
        self.request = request
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)

        self.paginator = paginator
        # TODO error handling
        page_number = int(self.get_page_number(request, paginator) or 1)
        self.page_number = page_number

        # The page number is used to calculate the cursor
        if page_number == 1:
            # For the first page, no cursor is needed
            return list(queryset.order_by(f"-{ordering_field}")[: self.page_size])

        offset = (page_number - 1) * self.page_size

        # Use a subquery to find the starting ID (avoiding full offset scan)
        start_id_qs = (
            queryset.order_by(f"-{ordering_field}")
            .values_list(ordering_field, flat=True)
            .distinct()[offset : offset + 1]
        )

        try:
            start_id = list(start_id_qs)[0]
        except IndexError:
            return []

        paginated_qs = queryset.filter(**{f"{ordering_field}__gte": start_id}).order_by(
            f"-{ordering_field}"
        )[: self.page_size]
        return list(paginated_qs)

    def get_paginated_response(self, data):
        # TODO implement count, next and previous page
        # next_page = self.page_number + 1 if len(data) == self.page_size else None
        # previous_page = self.page_number - 1 if self.page_number > 1 else None

        return Response(
            {
                "count": None,
                # 'count': self.paginator.count,
                # 'next': self.get_next_link() if next_page else None,
                # 'previous': self.get_previous_link() if previous_page else None,
                "results": data,
            }
        )


OptimizedPagination = (
    FuzzyPagination if settings.FUZZY_PAGINATION else CursorPageNumberPagination
)
