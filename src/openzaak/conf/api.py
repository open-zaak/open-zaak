from vng_api_common.conf.api import *  # noqa - imports white-listed

API_VERSION = "0.1.0"

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 100

SECURITY_DEFINITION_NAME = "JWT-Claims"

SWAGGER_SETTINGS = BASE_SWAGGER_SETTINGS.copy()
SWAGGER_SETTINGS.update(
    {
        "DEFAULT_INFO": "openzaak.components.zaken.api.schema.info",  # TODO: fix it as parameter
        'DEFAULT_AUTO_SCHEMA_CLASS': 'openzaak.utils.schema.AutoSchema',
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
    }
)

GEMMA_URL_INFORMATIEMODEL_VERSIE = "1.0"

repo = "vng-Realisatie/vng-referentielijsten"
commit = "da1b2cfdaadb2d19a7d3fc14530923913a2560f2"
REFERENTIELIJSTEN_API_SPEC = (
    f"https://raw.githubusercontent.com/{repo}/{commit}/src/openapi.yaml"
)  # noqa

ztc_repo = "vng-Realisatie/gemma-zaaktypecatalogus"
ztc_commit = "9c51082d6399060bff6bee2e23d0f22472bfa47f"
ZTC_API_SPEC = (
    f"https://raw.githubusercontent.com/{ztc_repo}/{ztc_commit}/src/openapi.yaml"
)  # noqa

drc_repo = "vng-Realisatie/gemma-documentregistratiecomponent"
drc_commit = "e82802907c24ea6a11a39c77595c29338d55e8c3"
DRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{drc_repo}/{drc_commit}/src/openapi.yaml"
)  # noqa

zrc_repo = "vng-Realisatie/gemma-zaakregistratiecomponent"
zrc_commit = "8ea1950fe4ec2ad99504d345eba60a175eea3edf"
ZRC_API_SPEC = (
    f"https://raw.githubusercontent.com/{zrc_repo}/{zrc_commit}/src/openapi.yaml"
)  # noqa
