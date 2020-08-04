# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from dictdiffer import diff
from vng_api_common.audittrails.models import AuditTrail


def format_dict_diff(changes):
    res = []
    for change in changes:
        if change[0] == "add" or change[0] == "remove":
            if not change[1]:
                res.append((change[0], dict(change[2])))
        elif change[0] == "change":
            res.append((change[0], {change[1]: change[2]}))
    return res


class AuditTrailMixin:
    @property
    def audittrail(self):
        qs = AuditTrail.objects.filter(
            hoofd_object__contains=self.get_absolute_api_url(version=1)
        ).order_by("-aanmaakdatum")
        res = []
        for audit in qs:
            oud = audit.oud or {}
            nieuw = audit.nieuw or {}

            changes = format_dict_diff(list(diff(oud, nieuw)))
            res.append((audit, changes))
        return res
