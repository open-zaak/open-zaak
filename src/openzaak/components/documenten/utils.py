# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import io
from decimal import Decimal
from io import BytesIO
from typing import TypeVar

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.functional import LazyObject

from drc_cmis.client_builder import get_cmis_client
from drc_cmis.models import Vendor
from privates.storages import PrivateMediaFileSystemStorage

# In the CMIS adapter, the Document object can be from either the Browser or Webservice binding module.
# So, this is to simplify the type hint
Cmisdoc = TypeVar("Cmisdoc")


class CMISStorageFile(File):
    def __init__(self, uuid_version):
        """
        :param uuid_version: A semi-colon-separated combination of the uuid and the document version,
        e.g. b09fac1f-f295-4b44-a94b-97126edec2f3;1.1
        """
        if uuid_version:
            self.file = io.BytesIO()
        else:
            self.file = None
        self.name = uuid_version
        self._is_read = False
        self._storage = CMISStorage()
        self._is_dirty = False

    @property
    def size(self):
        if not hasattr(self, "_size"):
            self._size = self._storage.size(self.name)
        return self._size

    def read(self, num_bytes=None):
        if not self._is_read:
            self.file = self._storage._read(self.name)
            self._is_read = True

        return self.file.read(num_bytes)

    def open(self, mode=None):
        if not self.closed:
            self.seek(0)
        elif self.name and self._storage.exists(self.name):
            self.file = self._storage._open(self.name, mode or self.mode)
        else:
            raise ValueError("The file cannot be reopened.")

    def close(self):
        if self._is_dirty:
            self._storage._save(self.name, self)
        self.file.close()


class CMISStorage(Storage):
    _cmis_client = None

    def __init__(self, location=None, base_url=None, encoding=None):
        pass

    @property
    def cmis_client(self):
        """
        Wrap the CMIS client in a property to defer initialization.

        The client is only initialized when it's actually needed, and then cached on the
        instance rather than initializing it when the storage is initialized. On fresh
        installations, the database has not migrated yet, and get_cmis_client needs the
        django-solo table configuration table to exist. See #972 for more information.
        """
        assert settings.CMIS_ENABLED, "CMIS is not enabled"
        if self._cmis_client is None:
            self._cmis_client = get_cmis_client()
        return self._cmis_client

    def _clear_cached_properties(self, setting, **kwargs):
        if setting == "CMIS_ENABLED":
            self._cmis_client = None
        if setting == "CMIS_URL_MAPPING_ENABLED":
            self._cmis_client = None

    def _open(self, uuid_version, mode="rb") -> CMISStorageFile:
        return CMISStorageFile(uuid_version)

    def _read(self, uuid_version: str) -> BytesIO:
        cmis_doc = self._get_cmis_doc(uuid_version)
        content_bytes = cmis_doc.get_content_stream()
        return content_bytes

    def size(self, uuid_version: str) -> int:
        cmis_doc = self._get_cmis_doc(uuid_version)
        return cmis_doc.bestandsomvang

    def url(self, uuid_version: str) -> str:
        # TODO create a custom link to support content URLs with SOAP
        if "cmisws" in self.cmis_client.base_url:
            raise RuntimeError(
                "Webservice CMIS binding does not support file content URLs"
            )

        cmis_doc = self._get_cmis_doc(uuid_version)

        # introspect repos
        repositories = self.cmis_client.get_request(self.cmis_client.base_url)
        for repo_config in repositories.values():
            if repo_config["repositoryUrl"] == self.cmis_client.base_url:
                break
        else:
            raise RuntimeError("Repository config not found for this client config!")

        vendor = repo_config["vendorName"]

        if vendor.lower() == Vendor.alfresco:
            # we know Alfresco URLs, we need the part before /api/
            base_url = self.cmis_client.base_url[
                : self.cmis_client.base_url.index("/api/")
            ]
            node_ref = cmis_doc.properties["alfcmis:nodeRef"]["value"]
            part = node_ref.replace("://", "/", 1)
            return f"{base_url}/s/api/node/content/{part}"
        else:
            raise NotImplementedError(f"CMIS vendor {vendor} is not implemented yet.")

    def _get_cmis_doc(self, uuid_version: str) -> Cmisdoc:
        uuid, wanted_version = uuid_version.split(";")
        wanted_version = int(Decimal(wanted_version))
        cmis_doc = self.cmis_client.get_document(drc_uuid=uuid)
        # only way to get a specific version
        if cmis_doc.versie != wanted_version:
            all_versions = self.cmis_client.get_all_versions(cmis_doc)
            for version in all_versions:
                if version.versie == wanted_version:
                    cmis_doc = version
                    break
        return cmis_doc


class PrivateMediaStorageWithCMIS(LazyObject):
    def _setup(self):
        if settings.CMIS_ENABLED:
            self._wrapped = CMISStorage()
        else:
            self._wrapped = PrivateMediaFileSystemStorage()


private_media_storage_cmis = PrivateMediaStorageWithCMIS()
