# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.notifications.kanaal import Kanaal
from openzaak.utils.help_text import mark_experimental

from ..models import Zaak

KANAAL_ZAKEN = Kanaal(
    "zaken",
    main_resource=Zaak,
    kenmerken=(
        "bronorganisatie",
        "zaaktype",
        "zaaktype.catalogus",
        "vertrouwelijkheidaanduiding",
    ),
    extra_kwargs={
        "zaaktype.catalogus": {
            "help_text": mark_experimental(
                "URL-referentie naar de CATALOGUS waartoe dit ZAAKTYPE behoort."
            )
        }
    },
)
