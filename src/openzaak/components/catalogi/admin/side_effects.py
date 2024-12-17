# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import uuid
from abc import ABC, abstractmethod
from datetime import date

from rest_framework.request import Request

from openzaak.utils.models import clone_object

from ..api.viewsets import (
    BesluitTypeViewSet,
    InformatieObjectTypeViewSet,
    ZaakTypeViewSet,
)
from ..models import BesluitType, InformatieObjectType, ZaakType

VIEWSET_FOR_MODEL = {
    ZaakType: ZaakTypeViewSet,
    InformatieObjectType: InformatieObjectTypeViewSet,
    BesluitType: BesluitTypeViewSet,
}


class SideEffectBase(ABC):
    def __init__(self, modeladmin, request, original, change, form):
        self.modeladmin = modeladmin
        self.request = request
        self.original = original
        self.change = change
        self.form = form

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # if anything went wrong, don't apply the side effects
        if exc_type is not None:
            return

        self.apply()

    @abstractmethod
    def apply(self):
        pass


class VersioningSideEffect(SideEffectBase):

    new_version = None

    def apply(self):
        if "_addversion" not in self.request.POST:
            return

        self.new_version = self.create_new_version()

    def create_new_version(self):
        new_obj = clone_object(self.original)
        version_date = date.today()

        new_obj.uuid = uuid.uuid4()
        new_obj.datum_begin_geldigheid = version_date
        new_obj.versiedatum = version_date
        new_obj.datum_einde_geldigheid = None
        new_obj.concept = True
        new_obj.save()

        related_objects = [
            f
            for f in new_obj._meta.get_fields(include_hidden=True)
            if (f.auto_created and not f.concrete)
        ]

        # related objects
        for relation in related_objects:
            if relation.name in self.modeladmin.exclude_copy_relation:
                continue

            # m2m relation included in the loop below as one_to_many
            if relation.one_to_many or relation.one_to_one:
                remote_model = relation.related_model
                remote_field = relation.field.name

                related_queryset = remote_model.objects.filter(
                    **{remote_field: self.original.pk}
                )
                for related_obj in related_queryset:
                    related_obj.pk = None
                    setattr(related_obj, remote_field, new_obj)

                    if hasattr(related_obj, "uuid"):
                        related_obj.uuid = uuid.uuid4()
                    related_obj.save()

        return new_obj


class NotificationSideEffect(SideEffectBase):
    def apply(self):
        viewset_cls = VIEWSET_FOR_MODEL[type(self.original)]
        viewset = viewset_cls(request=self.request)

        send_notification = False
        is_create = (
            (not self.change)
            or not self.original.pk
            or "_addversion" in self.request.POST
        )
        is_update = self.form.has_changed() or "_publish" in self.request.POST
        if is_create:
            send_notification = True
            viewset.action = "create"
        elif is_update:
            send_notification = True
            viewset.action = "update"

        if send_notification:
            reference_object = getattr(self, "new_version_instance", self.original)

            context_request = Request(self.request)
            # set versioning to context_request
            (
                context_request.version,
                context_request.versioning_scheme,
            ) = viewset.determine_version(context_request)

            data = viewset.serializer_class(
                reference_object, context={"request": context_request}
            ).data

            viewset.notify(status_code=200, data=data, instance=reference_object)
