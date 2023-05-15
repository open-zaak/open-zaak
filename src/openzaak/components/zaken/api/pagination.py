# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from collections import OrderedDict

from django.core.paginator import InvalidPage, Paginator as DjangoPaginator
from django.utils.functional import cached_property

from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination, _positive_int
from rest_framework.response import Response

from openzaak.config.models import FeatureFlags

PAGINATION_COUNT_LIMIT = 500


class ZaakPaginator(DjangoPaginator):
    @cached_property
    def count(self):
        """
        ⚡ restricts values to PK to remove implicit join from SQL query
        """
        feature_flags = FeatureFlags.get_solo()
        if feature_flags.improved_pagination_performance:
            offset = (_positive_int(self.page_number) - 1) * self.per_page
            return self.object_list.values("pk")[
                : offset + PAGINATION_COUNT_LIMIT
            ].count()
        return self.object_list.values("pk").count()


class ZaakPagination(PageNumberPagination):
    django_paginator_class = ZaakPaginator

    def get_paginated_response(self, data):
        response_data = [
            ("count", self.page.paginator.count),
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("results", data),
        ]

        feature_flags = FeatureFlags.get_solo()
        if feature_flags.improved_pagination_performance:
            # We can assume that the count is exact if it isn't a multiple of the page_size
            count_exact = self.page.paginator.count % self.page_size != 0
            response_data.insert(3, ("count_exact", count_exact))

        return Response(OrderedDict(response_data))

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = self.get_page_number(request, paginator)

        # Pass the page number to the paginator, to calculate the limit
        paginator.page_number = page_number

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)
