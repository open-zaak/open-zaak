import shutil

from unittest import TestCase
from pathlib import Path

from django.conf import settings

from openzaak.components.documenten.models import EnkelvoudigInformatieObject
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
        upload_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)
        files = upload_dir.glob("*")

        for file in files:
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)
