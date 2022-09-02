# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import uuid


def get_verzoek_response(verzoek: str) -> dict:
    return {
        "url": verzoek,
        "identificatie": "string",
        "bronorganisatie": "string",
        "externeIdentificatie": "string",
        "registratiedatum": "2022-07-20T13:56:29Z",
        "voorkeurskanaal": "string",
        "tekst": "string",
        "status": "ontvangen",
        "inTeTrekkenVerzoek": "http://example.com",
        "intrekkendeVerzoek": "http://example.com",
        "aangevuldeVerzoek": "http://example.com",
        "aanvullendeVerzoek": "http://example.com",
    }


def get_verzoekobject_response(verzoek: str, object_url: str, object_type: str) -> dict:
    verzoekobject_uuid = uuid.uuid4()
    return {
        "url": f"http://vrc.nl/api/v1/verzoekobject/{verzoekobject_uuid}",
        "verzoek": verzoek,
        "object": object_url,
        "objectType": object_type,
    }


def get_verzoekinformatieobject_response(informatieobject: str, verzoek: str) -> dict:
    vio_uuid = str(uuid.uuid4())
    return {
        "url": f"http://testserver/api/v1/verzoekinformatieobjecten/{vio_uuid}",
        "uuid": vio_uuid,
        "informatieobject": informatieobject,
        "verzoek": verzoek,
    }
