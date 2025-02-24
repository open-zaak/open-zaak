# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.notifications.kanaal import Kanaal
from openzaak.utils.help_text import mark_experimental

from ..models import EnkelvoudigInformatieObject

KANAAL_DOCUMENTEN = Kanaal(
    "documenten",
    main_resource=EnkelvoudigInformatieObject,
    kenmerken=(
        "bronorganisatie",
        "informatieobjecttype",
        "vertrouwelijkheidaanduiding",
        "informatieobjecttype.catalogus",
    ),
    extra_kwargs={
        "informatieobjecttype.catalogus": {
            "help_text": mark_experimental(
                "URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort."
            )
        }
    },
)
