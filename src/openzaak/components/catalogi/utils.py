# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import operator
from datetime import date
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.utils.translation import ugettext_lazy as _

from dateutil.relativedelta import relativedelta

from .models import Catalogus, ZaakType


def get_overlapping_zaaktypes(
    catalogus: Catalogus,
    omschrijving: str,
    begin_geldigheid: date,
    einde_geldigheid: Optional[date] = None,
    instance: Optional[ZaakType] = None,
) -> QuerySet:
    query = ZaakType.objects.filter(
        Q(catalogus=catalogus),
        Q(zaaktype_omschrijving=omschrijving),
        Q(datum_einde_geldigheid=None)
        | Q(datum_einde_geldigheid__gt=begin_geldigheid),  # noqa
    )
    if einde_geldigheid is not None:
        query = query.filter(datum_begin_geldigheid__lt=einde_geldigheid)

    if instance:
        query = query.exclude(pk=instance.pk)

    return query


def compare_relativedeltas(
    rd1: relativedelta, rd2: relativedelta, comparison=operator.gt
) -> bool:
    """
    Check if a relativedelta compares to another relativedelta.

    rd1 is the LHS, rd2 is the RHS in the comparison statement:
        rd1 > rd2

    See https://bugs.launchpad.net/dateutil/+bug/969928 for the edge cases that
    come into play, e.g. which is greater - 29 days or 1 month? In the context
    of zaaktypen, we compare from biggest (year) to smallest (day) unit.

    We expect two rd's to have the same precision specified, else we raise a
    validation error to block this. The admin interface exposes years, months
    and days by default.
    """

    # we only support > or < - if we get < -> swap the arguments to always
    # use > comparison
    assert comparison in (operator.gt, operator.lt)
    if comparison is operator.lt:
        rd1, rd2 = rd2, rd1

    # start comparing - first the dynamic attributes. We know that
    # 12 months = 1 year, doesn't matter how many days are in a month, so
    # convert to months
    rd1_months = (rd1.years * 12) + rd1.months
    rd2_months = (rd2.years * 12) + rd2.months

    # next - large minutes/hours numbers could amount to days or even months.
    # we don't support durations that amount to > 28 days (february, shortest month)
    # so as long as it stays below that, the comparison doesn't matter
    rd1_days_from_time = (rd1.minutes / 60 / 24) + (rd1.hours / 24)
    rd2_days_from_time = (rd2.minutes / 60 / 24) + (rd2.hours / 24)

    if rd1.months or rd2.months:
        if rd1_days_from_time > 28 or rd2_days_from_time > 28:
            raise ValidationError(
                _(
                    "A duration in hours/minutes amounts to more than 28 days. "
                    "Comparisons cannot be made because of this - you should specify this duration "
                    "in larger units (days/months/years)."
                ),
                code="vague-duration",
            )

    # we now need to look at the days attribute to figure out if that + the duration
    # from times amounts to > 28 (which would possibly put it over a month as well)
    # and prevent that.
    # However - this is only relevant if we're dealing with months at all
    if rd1.months or rd2.months:
        rd1_days = rd1.days + rd1_days_from_time
        rd2_days = rd2.days + rd2_days_from_time
        if rd1_days > 28 or rd2_days > 28:
            raise ValidationError(
                _(
                    "A duration in days/hours/minutes amounts to more than 28 days. "
                    "Comparisons cannot be made because of this - you should specify this duration "
                    "in larger units (days/months/years)."
                ),
                code="vague-duration",
            )

    # we finally know now that months is the unit with the major impact, smaller
    # units will not make it have more months -> we can compare!
    if rd1_months != rd2_months:
        return rd1_months > rd2_months

    # same amount of months -> look at the smaller units
    if rd1.days != rd2.days:
        return rd1.days > rd2.days

    # same amount of months and days -> look at hours
    if rd1.hours != rd2.hours:
        return rd1.hours > rd2.hours

    # minutes is the lowest we go, it's already an absurd case
    return rd1.minutes > rd2.minutes
