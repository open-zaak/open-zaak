import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = "generate DB rows based on csv files"

    def add_arguments(self, parser):
        parser.add_argument(
            '-t', '--table', dest='table',
            default='zaken_zaak', type=str,
            help='Name of the table in DB'
        )
        parser.add_argument(
            '-f', '--file', dest='file',
            default='zaken_10000.csv', type=str,
            help='Name of the csv file'
        )
        parser.add_argument(
            '-c', '--clean', dest='clean',
            default=False, action='store_true',
            help='Truncate the table before loading data'
        )

    def handle(self, table, file, clean, *args, **options):
        csv_dir = os.path.join(settings.DJANGO_PROJECT_DIR, 'performance_tests/fixtures')
        csv_file = os.path.join(csv_dir, file)

        sql = "copy {} from '{}' delimiter ';' CSV header;".format(table, csv_file)

        with connection.cursor() as cursor:
            if clean:
                cursor.execute(f"truncate table {table} cascade;")
            cursor.execute(sql)
