# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from vng_api_common.conf.api import *  # noqa - imports white-listed

# Remove the reference - we don't have a single API version.
del API_VERSION  # noqa

AUTORISATIES_API_VERSION = "1.0.0"
BESLUITEN_API_VERSION = "1.0.1"
CATALOGI_API_VERSION = "1.0.0"
DOCUMENTEN_API_VERSION = "1.0.1"
ZAKEN_API_VERSION = "1.0.2"

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 100

SECURITY_DEFINITION_NAME = "JWT-Claims"

SWAGGER_SETTINGS = BASE_SWAGGER_SETTINGS.copy()
SWAGGER_SETTINGS.update(
    {
        "DEFAULT_INFO": "openzaak.components.zaken.api.schema.info",  # TODO: fix it as parameter
        "DEFAULT_AUTO_SCHEMA_CLASS": "openzaak.utils.schema.AutoSchema",
        "SECURITY_DEFINITIONS": {
            SECURITY_DEFINITION_NAME: {
                # OAS 3.0
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                # not official...
                # 'scopes': {},  # TODO: set up registry that's filled in later...
                # Swagger 2.0
                # 'name': 'Authorization',
                # 'in': 'header'
                # 'type': 'apiKey',
            }
        },
        "DEFAULT_FIELD_INSPECTORS": (
            "vng_api_common.inspectors.geojson.GeometryFieldInspector",
            "vng_api_common.inspectors.files.FileFieldInspector",
            "openzaak.utils.inspectors.LengthHyperlinkedRelatedFieldInspector",
            "django_loose_fk.inspectors.fields.LooseFkFieldInspector",
        )
        + BASE_SWAGGER_SETTINGS["DEFAULT_FIELD_INSPECTORS"],
        "DEFAULT_FILTER_INSPECTORS": (
            "django_loose_fk.inspectors.query.FilterInspector",
        )
        + BASE_SWAGGER_SETTINGS["DEFAULT_FILTER_INSPECTORS"],
    }
)

GEMMA_URL_INFORMATIEMODEL_VERSIE = "1.0"

# TODO: deduplicate
repo = "vng-Realisatie/vng-referentielijsten"
commit = "4533cc71dcd17e997fce9e31445db852b7540321"
REFERENTIELIJSTEN_API_SPEC = (
    f"https://raw.githubusercontent.com/{repo}/{commit}/src/openapi.yaml"
)
VRL_API_SPEC = "https://selectielijst.openzaak.nl/api/v1/schema/openapi.yaml?v=3"

ztc_repo = "vng-Realisatie/gemma-zaaktypecatalogus"
ztc_commit = "d52ff0a8138b577e4f4516b0bd957354d91fb97c"
ZTC_API_SPEC = (
    f"https://raw.githubusercontent.com/{ztc_repo}/{ztc_commit}/src/openapi.yaml"
)

drc_repo = "vng-Realisatie/gemma-documentregistratiecomponent"
drc_commit = "7b3725282bfe694aee5b6dba6ae8bfb81cea0a5d"
DRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{drc_repo}/{drc_commit}/src/openapi.yaml"
)

zrc_repo = "vng-Realisatie/gemma-zaakregistratiecomponent"
zrc_commit = "d7c335084a1f25f92cbced253885de0f01896aa1"
ZRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{zrc_repo}/{zrc_commit}/src/openapi.yaml"
)

brc_repo = "vng-Realisatie/gemma-besluitregistratiecomponent"
brc_commit = "bf69bf643ce0c9146eeb014adc940e06948a8cac"
BRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{brc_repo}/{brc_commit}/src/openapi.yaml"
)


SPEC_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

LINK_FETCHER = "openzaak.nlx.fetcher"

# URLs for documentation that are shown in API schema
DOCUMENTATION_URL = "https://vng-realisatie.github.io/gemma-zaken/standaard/"
OPENZAAK_DOCS_URL = "https://open-zaak.readthedocs.io/en/latest/"
OPENZAAK_GITHUB_URL = "https://github.com/open-zaak/open-zaak"
ZGW_URL = "https://www.vngrealisatie.nl/producten/api-standaarden-zaakgericht-werken"
