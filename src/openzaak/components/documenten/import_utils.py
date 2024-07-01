# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from django.utils.functional import classproperty

from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.import_data.models import ImportRowResultChoices


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
    _zaak_uuid: str
    _trefwoorden: str

    row_index: int

    comment: Optional[str] = None
    instance: Optional[EnkelvoudigInformatieObject] = None

    _processed: bool = False
    _succeeded: bool = False

    def __str__(self):
        return f"Row {self.row_index} - {self.uuid}"

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
            "zaakUuid",
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
    def identificatie(self) -> str:
        if self.instance and self.instance.identificatie:
            return self.instance.identificatie
        return self._identificatie

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
    def imported_path(self) -> Optional[Path]:
        if not self.instance or not self.instance.inhoud.path:
            return

        return Path(self.instance.inhoud.path)

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
        if not any(
            (
                self._ondertekening_soort,
                self._ondertekening_datum,
            )
        ):
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
    def zaak_uuid(self) -> Optional[str]:
        return self._zaak_uuid

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
            "zaakUuid": self._zaak_uuid,
            "trefwoorden": self._trefwoorden,
        }

    def as_export_data(self):
        return {
            **self.as_original(),
            "uuid": self.uuid,
            "identificatie": self.identificatie,
            "opmerking": self.comment,
            "resultaat": self.result,
        }
