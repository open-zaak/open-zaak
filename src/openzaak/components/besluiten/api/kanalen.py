# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.notifications.kanaal import Kanaal
from openzaak.utils.help_text import mark_experimental

from ..models import Besluit

KANAAL_BESLUITEN = Kanaal(
    "besluiten",
    main_resource=Besluit,
    kenmerken=("verantwoordelijke_organisatie", "besluittype", "besluittype.catalogus"),
    extra_kwargs={
        "besluittype.catalogus": {
            "help_text": mark_experimental(
                "URL-referentie naar de CATALOGUS waartoe dit BESLUITTYPE behoort."
            )
        }
    },
)
