from django.conf import settings
from django.db.models import manager

from .query import (
    ObjectInformatieObjectQuerySet,
)
from .querysets import (
    CMISQuerySet,
    DjangoQuerySet,
    ObjectInformatieObjectCMISQuerySet,
    GebruiksrechtenQuerySet,
)


class AdapterManager(manager.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return CMISQuerySet(model=self.model, using=self._db, hints=self._hints)
        else:
            return DjangoQuerySet(model=self.model, using=self._db, hints=self._hints)


class GebruiksrechtenAdapterManager(manager.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return GebruiksrechtenQuerySet(
                model=self.model, using=self._db, hints=self._hints
            )
        else:
            return DjangoQuerySet(model=self.model, using=self._db, hints=self._hints)


class ObjectInformatieObjectAdapterManager(manager.Manager):
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
