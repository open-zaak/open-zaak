# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
import logging

from django.db.models import QuerySet

from django_filters import OrderingFilter as _OrderingFilter, constants
from vng_api_common.filtersets import FilterSet as _FilterSet

logger = logging.getLogger(__name__)


class FilterSet(_FilterSet):
    """
    Add help texts for model field filters
    """

    @classmethod
    def filter_for_field(cls, field, field_name, lookup_expr=None):
        filter = super().filter_for_field(field, field_name, lookup_expr)

        if not filter.extra.get("help_text"):
            filter.extra["help_text"] = getattr(field, "help_text", None)
        return filter


class OrderingFilter(_OrderingFilter):
    def filter(self, qs, value):
        if value in constants.EMPTY_VALUES:
            return qs

        ordering = [self.get_ordering_value(param) for param in value]
        return qs.order_by(*ordering).distinct()


class FilterGroup:
    """
    The work here is largely cherry-picked from this unmerged django-filters PR:
    https://github.com/carltongibson/django-filter/pull/1167/files
    """

    def __init__(self, filter_names):
        self.filter_names = filter_names

    def set_parent(self, parent):
        # Here we support assigning the parent FilterSet, so that we can access
        # implied filters directly with
        # `self.parent.filters["some_filter_name"]`.
        self.parent = parent

    def extract_data(self, cleaned_data):
        # Create a copy so as to not modify the original data dict.
        data = cleaned_data.copy()

        return {
            name: data.pop(name) for name in self.filter_names if name in data
        }, data

    def _filter_inputs(self, data):
        # - Sanity check that correct data has been provided by the
        #   filterset.
        assert set(data).issubset(
            set(self.filter_names)
        ), "The `data` must be a subset of the group's `.filters`."

        # - Remove empty values that would normally be skipped by the
        #   ``Filter.filter`` method.
        return {k: v for k, v in data.items() if v not in constants.EMPTY_VALUES}

    def filter(self, qs, **data):
        data = self._filter_inputs(data)

        if not data:
            return qs

        return self.apply_filters(qs, data)

    def apply_filters(self, qs, data):
        """
        This function can be overwritten by passing one into the init, which
        might be necessary in some cases. Overwriting it might require some
        complexities, such as needing to reimplement existing filter logic.
        The default implementation here applies each filter to the queryset,
        then calls a *magical* QuerySet._next_is_sticky() function
        (ref: https://blog.ionelmc.ro/2014/05/10/django-sticky-queryset-filters/).
        `_next_is_sticky()` has the effect of combining the next `qs.filter()`
        call as an AND instead of an OR, which is the counter-intuitive default
        for django orm. Note that this will break if any of the dependent filter
        functions call qs.filter multiple times, which might be a reasonable
        thing to do depending on the filter's use-case (e.g. unioning several
        qs.filter() calls). If that is the case, overwriting this function is
        supported as an escape hatch, tho it might be worth arguing to rewrite
        the filter in question - filters that need do this kind of thing should
        be expressable as Q()s that get built up and applied via one qs.filter()
        function.
        """
        for f_name, val in data.items():
            f = self.parent.filters[f_name]

            # the sticky of the icky
            qs._next_is_sticky()

            qs = f.filter(qs, val)

        return qs


class FilterSetWithGroups(FilterSet):
    """
    copied from https://gist.github.com/russmatney/7c757989ea3d6b1343df841ce5f33bc4

    related issue/PR in django_filters:
      https://github.com/carltongibson/django-filter/pull/1167
      https://github.com/carltongibson/django-filter/issues/745

    Django doc - https://docs.djangoproject.com/en/4.2/topics/db/queries/#spanning-multi-valued-relationships
    """

    groups = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.groups:
            logger.warn("FilterSetWithGroups used without any groups.")
        for group in self.groups:
            group.set_parent(self)

    def filter_queryset(self, queryset):
        """
        Here we overwrite the django-filters default FilterSet impl to extract
        fields that should be applied together. This prevents the extracted fields
        from being applied individually, and provides an opportunity for them to
        be applied as a group of filters.
        """

        cleaned_data = self.form.cleaned_data.copy()

        # Extract the grouped data from the rest of the `cleaned_data`. This
        # ensures that the original filter methods aren't called in addition
        # to the group filter methods.
        for group in self.groups:
            group_data, cleaned_data = group.extract_data(cleaned_data)
            queryset = group.filter(queryset, **group_data)

        for name, value in cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)
            assert isinstance(
                queryset, QuerySet
            ), "Expected '%s.%s' to return a QuerySet, but got a %s instead." % (
                type(self).__name__,
                name,
                type(queryset).__name__,
            )
        return queryset
