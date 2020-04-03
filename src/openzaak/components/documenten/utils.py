import io
from privates.storages import PrivateMediaFileSystemStorage
from drc_cmis.client import CMISDRCClient

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.functional import LazyObject


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
        if not hasattr(self, '_size'):
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

    def _open(self, uuid_version, mode="rb"):
        return CMISStorageFile(uuid_version)

    def _read(self, uuid_version):
        uuid, wanted_version = self._get_uuid_and_version(uuid_version)
        cmis_doc = self._client.get_cmis_document(
            identification=uuid,
            via_identification=False,
            filters=None
        )

        cmis_doc = self._get_correct_doc_version(cmis_doc, wanted_version)

        content_bytes = cmis_doc.get_content_stream()
        return content_bytes

    def size(self, uuid_version):
        content_bytes = self._read(uuid_version)
        return len(content_bytes.read())

    def url(self, uuid_version):
        uuid, wanted_version = self._get_uuid_and_version(uuid_version)

        cmis_doc = self._client.get_cmis_document(
            identification=uuid,
            via_identification=False,
            filters=None
        )

        cmis_doc = self._get_correct_doc_version(cmis_doc, wanted_version)

        # Example nodeRef: workspace://SpacesStore/b09fac1f-f295-4b44-a94b-97126edec2f3
        node_ref = cmis_doc.properties['alfcmis:nodeRef']['value']
        node_ref = node_ref.split("://")
        host_url = "http://localhost:8082/"
        content_base_url = "alfresco/s/api/node/content/"
        node_ref_url = node_ref[0] + "/" + node_ref[1]
        url = f"{host_url}{content_base_url}{node_ref_url}"
        return url

    def _get_uuid_and_version(self, uuid_version):
        uuid = uuid_version.split(";")[0]
        wanted_version = uuid_version.split(";")[1]
        return uuid, wanted_version

    def _get_correct_doc_version(self, cmis_doc, wanted_version):
        if cmis_doc.versie != wanted_version:
            all_versions = cmis_doc.get_all_versions()
            for version_number, cmis_document_version in all_versions.items():
                if version_number == wanted_version:
                    cmis_doc = cmis_document_version
                    break
        return cmis_doc


class PrivateMediaStorageWithCMIS(LazyObject):
    def _setup(self):
        if settings.CMIS_ENABLED:
            self._wrapped = CMISStorage()
        else:
            self._wrapped = PrivateMediaFileSystemStorage()


private_media_storage_cmis = PrivateMediaStorageWithCMIS()
