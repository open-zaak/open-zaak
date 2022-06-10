# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from vng_api_common.conf.api import *  # noqa - imports white-listed

from openzaak.api_standards import APIStandard

# Remove the reference - we don't have a single API version.
del API_VERSION  # noqa

AUTORISATIES_API_VERSION = "1.0.0"
BESLUITEN_API_VERSION = "1.1.0"
CATALOGI_API_VERSION = "1.2.1"
DOCUMENTEN_API_VERSION = "1.3.0"
ZAKEN_API_VERSION = "1.4.0"

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 100

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = REST_FRAMEWORK[
    "DEFAULT_RENDERER_CLASSES"
] + ("openzaak.utils.renderers.ProblemJSONRenderer",)


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
            "openzaak.utils.inspectors.IncludeSerializerInspector",
        )
        + BASE_SWAGGER_SETTINGS["DEFAULT_FIELD_INSPECTORS"],
        "DEFAULT_FILTER_INSPECTORS": (
            "django_loose_fk.inspectors.query.FilterInspector",
        )
        + BASE_SWAGGER_SETTINGS["DEFAULT_FILTER_INSPECTORS"],
    }
)

GEMMA_URL_INFORMATIEMODEL_VERSIE = "1.0"

COMMONGROUND_API_COMMON_GET_DOMAIN = "openzaak.utils.get_openzaak_domain"

#
# API's Open Zaak interacts with that have a defined standard (or community-accepted
# one when there's no official standard)
#

# TODO: deduplicate
vrl_ref = "4533cc71dcd17e997fce9e31445db852b7540321"
REFERENTIELIJSTEN_API_STANDARD = APIStandard(
    alias="vrl-0.5.6",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/vng-referentielijsten/{vrl_ref}/src/openapi.yaml"
    ),
    is_standardized=False,
)

SELECTIELIJST_API_STANDARD = APIStandard(
    alias="selectielijst-1.0.0",
    oas_url="https://selectielijst.openzaak.nl/api/v1/schema/openapi.yaml",
    is_standardized=False,
)

ztc_ref = "1.2.0"
ZTC_API_STANDARD = APIStandard(
    alias=f"catalogi-{ztc_ref}",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/catalogi-api/{ztc_ref}/src/openapi.yaml"
    ),
)

drc_ref = "1.0.1.post1"
DRC_API_STANDARD = APIStandard(
    alias=f"documenten-{drc_ref}",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/documenten-api/{drc_ref}/src/openapi.yaml"
    ),
)

zrc_ref = "1.0.3"
ZRC_API_STANDARD = APIStandard(
    alias=f"zaken-{zrc_ref}",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/zaken-api/{zrc_ref}/src/openapi.yaml"
    ),
)

brc_ref = "1.0.1.post0"
BRC_API_STANDARD = APIStandard(
    alias=f"besluiten-{brc_ref}",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/besluiten-api/{brc_ref}/src/openapi.yaml"
    ),
)

cmc_ref = "20f149a66163047b6ae3719709a600285fbb1c36"
CMC_API_STANDARD = APIStandard(
    alias="contactmomenten-2021-09-13",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/contactmomenten-api/{cmc_ref}/src/openapi.yaml"
    ),
    is_standardized=False,
)

vrc_ref = "57c83f6799df482f5c7fc70813d59264b9979619"
VRC_API_STANDARD = APIStandard(
    alias="verzoeken-2021-06-21",
    oas_url=(
        "https://raw.githubusercontent.com/"
        f"vng-Realisatie/verzoeken-api/{vrc_ref}/src/openapi.yaml"
    ),
    is_standardized=False,
)

COMPONENT_TO_API_SPEC_MAPPING = {
    "besluiten": BRC_API_SPEC,
    "catalogi": ZTC_API_SPEC,
    "documenten": DRC_API_SPEC,
    "zaken": ZRC_API_SPEC,
}

SPEC_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

LINK_FETCHER = "openzaak.nlx.fetcher"

# URLs for documentation that are shown in API schema
DOCUMENTATION_URL = "https://vng-realisatie.github.io/gemma-zaken/standaard/"
OPENZAAK_DOCS_URL = "https://open-zaak.readthedocs.io/en/latest/"
OPENZAAK_GITHUB_URL = "https://github.com/open-zaak/open-zaak"
ZGW_URL = "https://www.vngrealisatie.nl/producten/api-standaarden-zaakgericht-werken"
