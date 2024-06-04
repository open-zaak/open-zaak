import csv
import shutil
from pathlib import Path
from unittest import TestCase

from django.conf import settings

from celery.utils.text import StringIO

from openzaak.utils.fields import get_default_path


class ImportTestFileMixin(TestCase):
    def setUp(self):
        super().setUp()

        self.remove_upload_files()
        self.remove_import_files()

    def remove_import_files(self):
        import_dir = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR)
        files = import_dir.glob("*")

        for file in files:
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)

    def remove_upload_files(self):
        from openzaak.components.documenten.models import EnkelvoudigInformatieObject

        upload_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)
        files = upload_dir.glob("*")

        for file in files:
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)


def get_csv_data(rows: list[list], headers: list[str]) -> str:
    data = StringIO(newline="")

    with data as file:
        csv_writer = csv.writer(file, delimiter=",", quotechar='"')

        if headers:
            csv_writer.writerow(headers)

        for row in rows:
            csv_writer.writerow(row)

        return data.getvalue()
