import io
from typing import Tuple

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.functional import LazyObject

from drc_cmis.client import CMISDRCClient
from drc_cmis.cmis.drc_document import Document
from privates.storages import PrivateMediaFileSystemStorage


def parse_uuid_version(uuid_version: str) -> Tuple[str, int]:
    uuid, wanted_version = uuid_version.split(";")
    wanted_version = int(wanted_version)
    return uuid, wanted_version


class CMISStorageFile(File):
    def __init__(self, uuid_version):
        """
        :param uuid_version: A semi-colon-separated combination of the uuid and the document version,
        e.g. b09fac1f-f295-4b44-a94b-97126edec2f3;1.1
        """
        self.file = io.BytesIO()
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
    def __init__(self, location=None, base_url=None, encoding=None):
        self._client = CMISDRCClient()

    def _open(self, uuid_version, mode="rb") -> CMISStorageFile:
        return CMISStorageFile(uuid_version)

    def _read(self, uuid_version: str) -> bytes:
        uuid, wanted_version = parse_uuid_version(uuid_version)
        cmis_doc = self._get_cmis_doc(uuid_version)
        content_bytes = cmis_doc.get_content_stream()
        return content_bytes

    def size(self, uuid_version: str) -> int:
        uuid, wanted_version = parse_uuid_version(uuid_version)
        cmis_doc = self._get_cmis_doc(uuid_version)
        return cmis_doc.contentStreamLength

    def url(self, uuid_version: str) -> str:
        uuid, wanted_version = parse_uuid_version(uuid_version)

        cmis_doc = self._get_cmis_doc(uuid_version)

        # Example nodeRef: workspace://SpacesStore/b09fac1f-f295-4b44-a94b-97126edec2f3
        node_ref = cmis_doc.properties["alfcmis:nodeRef"]["value"]
        node_ref = node_ref.split("://")
        # TODO: configurable!
        # FIXME: no hardcoded URLs
        host_url = "http://localhost:8082/"
        content_base_url = "alfresco/s/api/node/content/"
        node_ref_url = node_ref[0] + "/" + node_ref[1]
        url = f"{host_url}{content_base_url}{node_ref_url}"
        return url

    def _get_cmis_doc(self, uuid_version: str) -> Document:
        uuid, wanted_version = parse_uuid_version(uuid_version)
        cmis_doc = self._client.get_cmis_document(uuid=uuid)
        # only way to get a specific version
        if cmis_doc.versie != wanted_version:
            all_versions = Document.get_all_versions(cmis_doc)
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
