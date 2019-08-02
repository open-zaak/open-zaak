import os
from django.conf import settings

from vng_api_common.management.commands import generate_swagger

SCHEMA_MAPPING = {
    'info': 'openzaak.components.{}.api.schema.info',
    'urlconf': 'openzaak.components.{}.api.urls',
    'output': './src/openzaak/components/{}/swagger2.0.json',
    'output_md': './src/openzaak/components/{}/resources.md',
}


class Command (generate_swagger.Command):
    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--component', dest='component', default=None,
            help='The component name to define urlconf, base_path and schema info'
        )

    def handle(self, output_file, overwrite, format, api_url, mock, user, private, info, urlconf, component=None,
               *args, **options):

        if not component:
            super().handle(output_file, overwrite, format, api_url, mock, user, private, info, urlconf,
                           *args, **options)

        # rewrite command arguments based on the component
        info = SCHEMA_MAPPING['info'].format(component)
        urlconf = SCHEMA_MAPPING['urlconf'].format(component)

        if options['to_markdown_table']:
            output_file = SCHEMA_MAPPING['output_md'].format(component)
        else:
            output_file = SCHEMA_MAPPING['output'].format(component)

        # generate schema
        super().handle(output_file, overwrite, format, api_url, mock, user, private, info, urlconf,
                       *args, **options)


