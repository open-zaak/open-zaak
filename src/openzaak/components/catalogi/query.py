# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.db import models


class GeldigheidQuerySet(models.QuerySet):
    def with_dates(self, id_field="omschrijving"):
        """
        annotate queryset with begin_object and einde_object
        """
        qs = self.filter(
            catalogus=models.OuterRef("catalogus"),
            **{id_field: models.OuterRef(id_field)}
        )
        return self.annotate(
            datum_begin_object=models.Subquery(
                qs.order_by("datum_begin_geldigheid").values("datum_begin_geldigheid")[
                    :1
                ]
            ),
            datum_einde_object=models.Subquery(
                qs.order_by("-datum_begin_geldigheid").values("datum_einde_geldigheid")[
                    :1
                ]
            ),
        )
