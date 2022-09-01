# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings
from django.db import models

from .query.cmis import (
    CMISQuerySet,
    GebruiksrechtenQuerySet,
    ObjectInformatieObjectCMISQuerySet,
)
from .query.django import (
    DjangoQuerySet,
    InformatieobjectRelatedQuerySet,
    ObjectInformatieObjectQuerySet,
)


class AdapterManager(models.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return CMISQuerySet(model=self.model, using=self._db, hints=self._hints)
        else:
            return DjangoQuerySet(model=self.model, using=self._db, hints=self._hints)


class GebruiksrechtenAdapterManager(models.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return GebruiksrechtenQuerySet(
                model=self.model, using=self._db, hints=self._hints
            )
        else:
            return InformatieobjectRelatedQuerySet(
                model=self.model, using=self._db, hints=self._hints
            )


class ObjectInformatieObjectAdapterManager(models.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return ObjectInformatieObjectCMISQuerySet(
                model=self.model, using=self._db, hints=self._hints
            )
        else:
            return ObjectInformatieObjectQuerySet(
                model=self.model, using=self._db, hints=self._hints
            )

    def create_from(self, relation):
        return self.get_queryset().create_from(relation)

    def delete_for(self, relation):
        return self.get_queryset().delete_for(relation)
