# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from vng_api_common.conf.api import BASE_REST_FRAMEWORK  # noqa: F401

from openzaak.api_standards import APIStandard

AUTORISATIES_API_VERSION = "1.0.0"
BESLUITEN_API_VERSION = "1.1.0"
CATALOGI_API_VERSION = "1.3.1"
DOCUMENTEN_API_VERSION = "1.4.2"
ZAKEN_API_VERSION = "1.5.1"

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 100

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = REST_FRAMEWORK[
    "DEFAULT_RENDERER_CLASSES"
] + ("openzaak.utils.renderers.ProblemJSONRenderer",)

REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "openzaak.utils.schema.AutoSchema"


SECURITY_DEFINITION_NAME = "JWT-Claims"
OPENZAAK_API_CONTACT_EMAIL = "support@maykinmedia.nl"
OPENZAAK_API_CONTACT_URL = "https://www.maykinmedia.nl"

SPECTACULAR_SETTINGS = {
    "REDOC_DIST": "SIDECAR",
    # info object
    "TITLE": "Open Zaak API",
    "LICENSE": {"name": "EUPL 1.2", "url": "https://opensource.org/licenses/EUPL-1.2"},
    "CONTACT": {"email": OPENZAAK_API_CONTACT_EMAIL, "url": OPENZAAK_API_CONTACT_URL},
    "SERVE_INCLUDE_SCHEMA": False,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
    ],
    "PREPROCESSING_HOOKS": ["openzaak.utils.hooks.preprocess_exclude_endpoints"],
    "SCHEMA_PATH_PREFIX": "/v1",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            SECURITY_DEFINITION_NAME: {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "ENUM_GENERATE_CHOICE_DESCRIPTION": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "DEFAULT_GENERATOR_CLASS": "openzaak.utils.generators.SchemaGenerator",
}


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
EXTERNAL_API_MAPPING = {
    "besluiten": BRC_API_STANDARD,
    "catalogi": ZTC_API_STANDARD,
    "documenten": DRC_API_STANDARD,
    "zaken": ZRC_API_STANDARD,
}

SPEC_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

LINK_FETCHER = "openzaak.nlx.fetcher"

# URLs for documentation that are shown in API schema
DOCUMENTATION_URL = "https://vng-realisatie.github.io/gemma-zaken/standaard/"
OPENZAAK_DOCS_URL = "https://open-zaak.readthedocs.io/en/latest/"
OPENZAAK_GITHUB_URL = "https://github.com/open-zaak/open-zaak"
ZGW_URL = "https://www.vngrealisatie.nl/producten/api-standaarden-zaakgericht-werken"
