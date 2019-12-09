from vng_api_common.conf.api import *  # noqa - imports white-listed

API_VERSION = "1.0.0"

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
commit = "da1b2cfdaadb2d19a7d3fc14530923913a2560f2"
REFERENTIELIJSTEN_API_SPEC = (
    f"https://raw.githubusercontent.com/{repo}/{commit}/src/openapi.yaml"
)
VRL_API_SPEC = "https://referentielijsten-api.vng.cloud/api/v1/schema/openapi.yaml?v=3"

ztc_repo = "vng-Realisatie/gemma-zaaktypecatalogus"
ztc_commit = "d0a874ca1e876e61e812021c502548ee890767d1"
ZTC_API_SPEC = (
    f"https://raw.githubusercontent.com/{ztc_repo}/{ztc_commit}/src/openapi.yaml"
)

drc_repo = "vng-Realisatie/gemma-documentregistratiecomponent"
drc_commit = "7b3725282bfe694aee5b6dba6ae8bfb81cea0a5d"
DRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{drc_repo}/{drc_commit}/src/openapi.yaml"
)

zrc_repo = "vng-Realisatie/gemma-zaakregistratiecomponent"
zrc_commit = "1842e7f2390b385b86904c842d26023a71330143"
ZRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{zrc_repo}/{zrc_commit}/src/openapi.yaml"
)

SPEC_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

REFERENTIELIJSTEN_API = {
    "scheme": "https",
    "host": "referentielijsten-api.vng.cloud",
}
