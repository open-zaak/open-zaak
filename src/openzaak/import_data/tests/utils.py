# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import csv
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from django.conf import settings
from django.test import override_settings

from celery.utils.text import StringIO

from openzaak.import_data.tests.factories import ImportFactory
from openzaak.utils.fields import get_default_path


class ImportTestMixin(TestCase):
    clean_documenten_files: bool
    clean_import_files: bool

    def setUp(self):
        super().setUp()

        self.temp_dir = get_temporary_dir()
        self.override = override_settings(IMPORT_DOCUMENTEN_BASE_DIR=self.temp_dir)
        self.override.enable()

        def _remove_temp_dir():
            shutil.rmtree(self.temp_dir)

        self.addCleanup(_remove_temp_dir)

        if self.clean_documenten_files:
            self.addCleanup(self.remove_documenten_files)

        if self.clean_import_files:
            self.addCleanup(self.remove_import_files)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        import_dir = cls._get_import_dir()
        documenten_dir = cls._get_documenten_dir()

        if cls.clean_import_files and import_dir.exists():
            shutil.rmtree(import_dir)

        if cls.clean_documenten_files and documenten_dir.exists():
            shutil.rmtree(documenten_dir)

    @classmethod
    def _get_import_dir(cls) -> Path:
        import_dir = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR)
        base_dir = Path(settings.BASE_DIR)

        if import_dir == base_dir or not import_dir.is_relative_to(base_dir):
            raise ValueError(
                "Path equals `BASE_DIR` or does not seem to be relative to "
                f"`BASE_DIR`. Not removing any files from {import_dir}"
            )

        return import_dir

    @classmethod
    def _get_documenten_dir(cls) -> Path:
        from openzaak.components.documenten.models import EnkelvoudigInformatieObject

        upload_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)

        if not upload_dir.is_relative_to(settings.PRIVATE_MEDIA_ROOT):
            raise ValueError(
                "Path does not seem to be relative to `PRIVATE_MEDIA_ROOT`. Not "
                f"removing any files from {upload_dir}"
            )

        return upload_dir

    def remove_import_files(self):
        """
        Removes all files that are referenced in the import metadata file
        """
        import_dir = self._get_import_dir()
        files = import_dir.glob("*")

        for file in files:
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)

    def remove_documenten_files(self):
        """
        Removes the files that are linked to EIO's
        """
        upload_dir = self._get_documenten_dir()
        files = upload_dir.glob("*")

        for file in files:
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)

    def create_import(self, **kwargs):
        instance = ImportFactory(**kwargs)

        if instance.report_file:
            path = Path(instance.report_file.path)
            self.addCleanup(path.unlink)

        if instance.import_file:
            path = Path(instance.import_file.path)
            self.addCleanup(path.unlink)

        return instance


def get_temporary_dir() -> str:
    return tempfile.mkdtemp(dir=settings.BASE_DIR)


def get_temporary_file() -> str:
    _, path = tempfile.mkstemp(dir=settings.BASE_DIR)
    return path


def get_csv_data(rows: list[list], headers: list[str]) -> str:
    data = StringIO(newline="")

    with data as file:
        csv_writer = csv.writer(file, delimiter=",", quotechar='"')

        if headers:
            csv_writer.writerow(headers)

        for row in rows:
            csv_writer.writerow(row)

        return data.getvalue()
