# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.urls import set_script_prefix

from vng_api_common.generators import OpenAPISchemaGenerator
from vng_api_common.management.commands import generate_swagger

SCHEMA_MAPPING = {
    "info": "openzaak.components.{}.api.schema.info",
    "urlconf": "openzaak.components.{}.api.urls",
}


class Command(generate_swagger.Command):
    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--component",
            dest="component",
            default=None,
            help="The component name to define urlconf, base_path and schema info",
        )

    def get_schema_generator(
        self, generator_class_name, api_info, api_version, api_url
    ):
        return OpenAPISchemaGenerator(info=api_info, url=api_url, urlconf=self.urlconf)

    def handle(
        self,
        output_file,
        overwrite,
        format,
        api_url,
        mock,
        api_version,
        user,
        private,
        generator_class_name,
        info,
        urlconf,
        component=None,
        **options,
    ):
        _version = getattr(settings, f"{component.upper()}_API_VERSION")

        # Setting must exist for vng-api-common, so monkeypatch it in
        settings.API_VERSION = _version

        if settings.SUBPATH:
            set_script_prefix(settings.SUBPATH)

        if not component:
            super().handle(
                output_file,
                overwrite,
                format,
                api_url,
                mock,
                api_version,
                user,
                private,
                generator_class_name,
                info,
                urlconf,
                **options,
            )

        # rewrite command arguments based on the component
        info = SCHEMA_MAPPING["info"].format(component)
        self.urlconf = SCHEMA_MAPPING["urlconf"].format(component)

        # generate schema
        super().handle(
            output_file,
            overwrite,
            format,
            api_url,
            mock,
            api_version,
            user,
            private,
            generator_class_name,
            info=info,
            urlconf=self.urlconf,
            **options,
        )
