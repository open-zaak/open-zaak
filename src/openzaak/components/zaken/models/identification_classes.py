# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers

from abc import ABC, abstractmethod
from datetime import date

from django.conf import settings
from django.db.models import Max
from django.db.models.functions import Length

from openzaak.utils.db import pg_advisory_lock

from .identification import ZaakIdentificatie

LOCK_ID_IDENTIFICATION_GENERATION = "generate-zaak-identification"


class BaseIdentificatie(ABC):
    def __init__(self, organisation: str, **kwargs):
        self.organisation = organisation

        self.model = ZaakIdentificatie

    @abstractmethod
    def current(self) -> str:
        pass

    @abstractmethod
    def _next(self, current_identificatie: str) -> str:
        pass

    def generate(self):
        """
        Generate an identification based on existing data.

        This uses a PostgreSQL-specific advisory lock, meaning that only one
        thread/process is able to generate a new identification at a time (other
        threads will simply wait until they acquire the lock after the running call
        releases it when the transaction exits).

        Note that this does NOT prevent other records from being read or even written
        to the involved table, so IntegrityError can still be raised if unique
        constraints will be violated. However, this does allow for concurrent read
        and writes with explicit identifications to different rows that don't affect
        the ID generation and should be a better option for performance than pessimistic
        locking where the entire table is locked even for reading (as otherwise the view
        of the data inside by generate_unique_identification could be stale due to new
        inserts).
        """
        with pg_advisory_lock(LOCK_ID_IDENTIFICATION_GENERATION):
            return self.model.objects.create(
                identificatie=self._next(self.current()),
                bronorganisatie=self.organisation,
            )

    def generate_bulk(self, amount: int):
        """
        Bulk generate multiple unique identificaties.

        This method uses the same PostgreSQL advisory lock to avoid race conditions
        and ensures identificaties are unique even when called concurrently.

        :param organisation: The organisation (bronorganisatie) to use.
        :param date: The date to include in the identificatie.
        :param amount: How many identificaties to generate.
        :return: List of created ZaakIdentificatie instances.
        """
        with pg_advisory_lock(LOCK_ID_IDENTIFICATION_GENERATION):
            next_identificatie = self.current()

            instances = []
            for i in range(amount):
                next_identificatie = self._next(next_identificatie)

                instance = self.model(
                    identificatie=next_identificatie,
                    bronorganisatie=self.organisation,
                )
                instances.append(instance)

            return self.model.objects.bulk_create(instances)


class YearIdentification(BaseIdentificatie):
    def __init__(self, organisation: str, date: date, **kwargs):
        super().__init__(organisation, **kwargs)

        self.prefix = f"ZAAK-{date.year}"

    def current(self) -> str:
        pattern = self.prefix + r"-\d{10}"

        # ⚡ start_with is added to use index in DB query
        issued_ids_for_year = self.model.objects.filter(
            identificatie__startswith=self.prefix, identificatie__regex=pattern
        )
        max_id = issued_ids_for_year.aggregate(Max("identificatie"))[
            "identificatie__max"
        ]

        return max_id or f"{self.prefix}-{''.zfill(10)}"

    def _next(self, current_identificatie: str) -> str:
        number = int(current_identificatie.split("-")[-1]) + 1
        return f"{self.prefix}-{str(number).zfill(10)}"


class CreationYearIdentification(YearIdentification):
    def __init__(self, bronorganisatie: str, **kwargs):
        super().__init__(bronorganisatie, date.today(), **kwargs)


class StartDatumYearIdentification(YearIdentification):
    def __init__(self, bronorganisatie: str, startdatum: date, **kwargs):
        super().__init__(bronorganisatie, startdatum, **kwargs)


class UWVIdentification(BaseIdentificatie):
    """
    Custom zaak identification for UWV

    A00000000 -> Z99999999 -> AA99999999 -> AB99999999 -> ZZ99999999

    `elfproef` is used for validation, each char is multiplied by its position (1-9 or 10), and
    letters have the value 0-25. The remainer of the total is divided by 11 and should be 10.

    Examples:
        A00000005 = 0*1 + 5*9 -> 45 mod 11 -> 1 INVALID
        A00000006 = 0*1 + 6*9 -> 54 mod 11 -> 10 VALID
        Z99999990 = 25*1 + 9*35 -> 340 mod 11 -> 10 VALID
        AA0000001 = 0*1 + 0*2 + 1*10 -> 10 mod 10 -> 10 VALID

    """

    def current(self):
        pattern = r"[A-Z]{1,2}[0-9]{8}"
        max_id = (
            self.model.objects.filter(identificatie__regex=pattern)
            .order_by(-Length("identificatie"), "-identificatie")
            .values_list("identificatie", flat=True)
            .first()
        )

        return max_id or "A00000005"

    def _split(self, identificatie: str):
        chars = identificatie.strip("0123456789")
        digits = identificatie[len(chars) :]
        return chars, digits

    def _validate(self, identificatie: str):
        chars, digits = self._split(identificatie)

        check = 0
        i = 1
        for c in chars:
            check += (ord(c) - 65) * i
            i += 1

        for d in digits:
            check += int(d) * i
            i += 1

        return check % 11 == 10

    def _increase(self, identificatie: str):
        def increase_char(char: str):
            return chr(ord(char) + 1)

        chars, digits = self._split(identificatie)

        if digits != "99999999":
            digits = str(int(digits) + 1).zfill(8)

        else:
            digits = "00000000"
            if len(chars) == 1:
                if chars == "Z":
                    chars = "AA"
                else:
                    chars = increase_char(chars)
            else:
                if chars[1] == "Z":
                    if chars[0] == "Z":
                        raise ValueError("Max identification reached")
                    chars = increase_char(chars[0]) + chars[1]
                else:
                    chars = chars[0] + increase_char(chars[1])

        return f"{chars}{digits}"

    def _next(self, current_identificatie: str) -> str:
        next_identificatie = self._increase(current_identificatie)
        while not self._validate(next_identificatie):
            next_identificatie = self._increase(next_identificatie)
        return next_identificatie


def get_base_identification_class():
    match settings.ZAAK_IDENTIFICATIE_GENERATOR:
        case "use-uvw-identification":
            identification_class = UWVIdentification
        case _:
            identification_class = YearIdentification

    return identification_class
