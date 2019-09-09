import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "generate DB rows based on csv files"

    def add_arguments(self, parser):
        parser.add_argument(
            "-t",
            "--table",
            dest="table",
            default="zaken_zaak",
            type=str,
            help="Name of the table in DB",
        )
        parser.add_argument(
            "-f",
            "--file",
            dest="file",
            default="test_data/zaken_10000.csv",
            type=str,
            help="Name of the csv file",
        )
        parser.add_argument(
            "-c",
            "--clean",
            dest="clean",
            default=False,
            action="store_true",
            help="Truncate the table before loading data",
        )

    def handle(self, table, file, clean, *args, **options):
        csv_file = os.path.join(settings.BASE_DIR, file)

        sql = "copy {} from '{}' delimiter ';' CSV header;".format(table, csv_file)

        with connection.cursor() as cursor:
            if clean:
                # truncate table
                cursor.execute(f"truncate table {table} cascade;")
            # load data from csv
            cursor.execute(sql)

            # set sequence counter
            cursor.execute(f"select id from {table} order by id desc limit 1;")
            last_id = cursor.fetchone()[0]
            cursor.execute(f"select setval('{table}_id_seq', {last_id});")
