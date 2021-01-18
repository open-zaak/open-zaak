# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.utils.permissions import AuthRequired


class BesluitAuthRequired(AuthRequired):
    """
    Look at the scopes required for the current action and at besluittype
    of current besluit and check that they are present in the AC for this client
    """

    permission_fields = ("besluittype",)
    main_resource = "openzaak.components.besluiten.api.viewsets.BesluitViewSet"
