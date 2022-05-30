# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.utils.translation import gettext_lazy as _

from rest_framework import authentication, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from openzaak.selectielijst.admin_fields import get_selectielijst_resultaat_choices
from openzaak.selectielijst.api import get_procestypen
from openzaak.selectielijst.models import ReferentieLijstConfig

from ...admin.forms import EMPTY_SELECTIELIJSTKLASSE_CHOICES
from ...models import ZaakType


class SelectielijstResultatenListView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAdminUser,)
    schema = None  # keep it undocumented

    def get(self, request, *args, **kwargs):
        try:
            zaaktype_id = int(request.GET.get("zaaktype", ""))
        except ValueError:
            raise ValidationError(
                {"zaaktype": _("Provide a valid zaaktype ID to filter for")}
            )

        zaaktype = ZaakType.objects.filter(pk=zaaktype_id).first()
        if zaaktype is None:
            raise ValidationError({"zaaktype": _("Could not find the zaaktype")})

        if not (url := zaaktype.selectielijst_procestype):
            return Response(list(EMPTY_SELECTIELIJSTKLASSE_CHOICES))

        choices = get_selectielijst_resultaat_choices(url)
        return Response(choices)


class SelectielijstProcestypenListView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAdminUser,)
    schema = None  # keep it undocumented

    def get(self, request, *args, **kwargs):
        try:
            year = int(request.GET.get("year", ""))
        except ValueError:
            raise ValidationError({"year": _("Provide a valid year to filter for")})

        config = ReferentieLijstConfig.get_solo()
        if year not in config.allowed_years:
            raise ValidationError(
                {
                    "year": _(
                        "Provide a valid year to filter for, must be one of: {valid_years}."
                    ).format(
                        valid_years=", ".join([str(x) for x in config.allowed_years])
                    )
                }
            )

        procestypen = get_procestypen(procestype_jaar=year)
        return Response(procestypen)
