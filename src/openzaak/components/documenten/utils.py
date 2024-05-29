# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from dataclasses import dataclass
import io
from decimal import Decimal
from io import BytesIO
from typing import Optional, TypeVar

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.functional import LazyObject, classproperty

from drc_cmis.client_builder import get_cmis_client
from drc_cmis.models import Vendor
from privates.storages import PrivateMediaFileSystemStorage

from openzaak.import_data.models import ImportRowResultChoices

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
        for repo_id, repo_config in repositories.items():
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


@dataclass
class DocumentRow:
    _uuid: str
    _identificatie: str
    _bronorganisatie: str
    _creatiedatum: str
    _titel: str
    _vertrouwelijkheidaanduiding: str
    _auteur: str
    _status: str
    _formaat: str
    _taal: str

    _bestandsnaam: str
    _bestandsomvang: str
    _bestandspad: str

    _link: str
    _beschrijving: str
    _ontvangstdatum: str
    _verzenddatum: str
    _indicatie_gebruiksrecht: str
    _verschijningsvorm: str

    _ondertekening_soort: str
    _ondertekening_datum: str

    _integriteit_algoritme: str
    _integriteit_waarde: str
    _integriteit_datum: str

    _informatieobjecttype: str
    _zaak_id: str
    _trefwoorden: str

    row_index: int

    comment: Optional[str] = None
    instance: Optional["EnkelvoudigInformatieObject"] = None

    _processed: bool = False
    _succeeded: bool = False

    @classproperty
    def import_headers(cls) -> list[str]:
        return [
            "uuid",
            "identificatie",
            "bronorganisatie",
            "creatiedatum",
            "titel",
            "vertrouwelijkheidaanduiding",
            "auteur",
            "status",
            "formaat",
            "taal",
            "bestandsnaam",
            "bestandsomvang",
            "bestandspad",
            "link",
            "beschrijving",
            "ontvangstdatum",
            "verzenddatum",
            "indicatieGebruiksrecht",
            "verschijningsvorm",
            "ondertekening.soort",
            "ondertekening.datum",
            "integriteit.algoritme",
            "integriteit.waarde",
            "integriteit.datum",
            "informatieobjecttype",
            "zaakId",
            "trefwoorden",
        ]

    @classproperty
    def export_headers(cls) -> list[str]:
        return [*cls.import_headers, "opmerking", "resultaat"]

    @property
    def uuid(self) -> str:
        if self.instance and self.instance.uuid:
            return str(self.instance.uuid)
        return self._uuid

    @property
    def bronorganisatie(self) -> str:
        return self._bronorganisatie

    @property
    def creatiedatum(self) -> Optional[str]:
        return self._creatiedatum or None

    @property
    def titel(self) -> Optional[str]:
        return self._titel or None

    @property
    def auteur(self) -> Optional[str]:
        return self._auteur or None

    @property
    def taal(self) -> Optional[str]:
        return self._taal or None

    @property
    def bestandspad(self) -> str:
        return self._bestandspad

    @property
    def bestandsomvang(self) -> Optional[int]:
        if not self._bestandsomvang:
            return None

        return int(self._bestandsomvang)

    @property
    def ontvangstdatum(self) -> Optional[str]:
        return self._ontvangstdatum or None

    @property
    def verzenddatum(self) -> Optional[str]:
        return self._verzenddatum or None

    @property
    def indicatie_gebruiksrecht(self) -> bool:
        return self._indicatie_gebruiksrecht in ("True", "true")

    @property
    def ondertekening(self) -> Optional[dict]:
        if not any((self._ondertekening_soort, self._ondertekening_datum,)):
            return None

        return {
            "soort": self._ondertekening_soort,
            "datum": self._ondertekening_datum,
        }

    @property
    def integriteit(self) -> Optional[dict]:
        if not any(
            (
                self._integriteit_datum,
                self._integriteit_waarde,
                self._integriteit_algoritme,
            )
        ):
            return None

        return {
            "algoritme": self._integriteit_algoritme,
            "waarde": self._integriteit_waarde,
            "datum": self._integriteit_datum,
        }

    @property
    def zaak_id(self) -> Optional[str]:
        return self._zaak_id

    @property
    def trefwoorden(self) -> list[str]:
        if not self._trefwoorden:
            return []

        trefwoorden = self._trefwoorden.replace('"', "")

        if not trefwoorden:
            return []

        return trefwoorden.split(",")

    @property
    def processed(self) -> bool:
        return self._processed

    @processed.setter
    def processed(self, value: bool):
        self._processed = value

    @property
    def succeeded(self) -> bool:
        return self.processed and self._succeeded

    @succeeded.setter
    def succeeded(self, value: bool):
        self._succeeded = value

    @property
    def failed(self) -> bool:
        return self.processed and not self.succeeded

    @property
    def has_instance(self) -> bool:
        return bool(self.instance and self.instance.pk)

    @property
    def result(self):
        if self.succeeded:
            return ImportRowResultChoices.imported.label

        return ImportRowResultChoices.not_imported.label

    def as_serializer_data(self):
        return {
            "identificatie": self._identificatie,
            "bronorganisatie": self.bronorganisatie,
            "creatiedatum": self.creatiedatum,
            "titel": self.titel,
            "vertrouwelijkheidaanduiding": self._vertrouwelijkheidaanduiding,
            "auteur": self.auteur,
            "status": self._status,
            "formaat": self._formaat,
            "taal": self.taal,
            "bestandsnaam": self._bestandsnaam,
            "bestandsomvang": self.bestandsomvang,
            "link": self._link,
            "beschrijving": self._beschrijving,
            "ontvangstdatum": self.ontvangstdatum,
            "verzenddatum": self.verzenddatum,
            "indicatie_gebruiksrecht": self.indicatie_gebruiksrecht,
            "verschijningsvorm": self._verschijningsvorm,
            "ondertekening": self.ondertekening,
            "integriteit": self.integriteit,
            "informatieobjecttype": self._informatieobjecttype,
            "trefwoorden": self.trefwoorden,
        }

    def as_original(self):
        return {
            "uuid": self._uuid,
            "identificatie": self._identificatie,
            "bronorganisatie": self._bronorganisatie,
            "creatiedatum": self._creatiedatum,
            "titel": self._titel,
            "vertrouwelijkheidaanduiding": self._vertrouwelijkheidaanduiding,
            "auteur": self._auteur,
            "status": self._status,
            "formaat": self._formaat,
            "taal": self._taal,
            "bestandsnaam": self._bestandsnaam,
            "bestandsomvang": self._bestandsomvang,
            "bestandspad": self._bestandspad,
            "link": self._link,
            "beschrijving": self._beschrijving,
            "ontvangstdatum": self._ontvangstdatum,
            "verzenddatum": self._verzenddatum,
            "indicatieGebruiksrecht": self._indicatie_gebruiksrecht,
            "verschijningsvorm": self._verschijningsvorm,
            "ondertekening.soort": self._ondertekening_soort,
            "ondertekening.datum": self._ondertekening_datum,
            "integriteit.algoritme": self._integriteit_algoritme,
            "integriteit.waarde": self._integriteit_waarde,
            "integriteit.datum": self._integriteit_datum,
            "informatieobjecttype": self._informatieobjecttype,
            "zaakId": self._zaak_id,
            "trefwoorden": self._trefwoorden,
        }

    def as_export_data(self):
        return {
            **self.as_original(),
            "uuid": self.uuid,
            "opmerking": self.comment,
            "resultaat": self.result,
        }


