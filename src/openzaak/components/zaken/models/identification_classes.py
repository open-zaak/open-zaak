# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers

from abc import ABC, abstractmethod
from datetime import date
from itertools import chain, count, islice, starmap
from operator import mul
from typing import Generator

from django.conf import settings
from django.db.models import Max
from django.db.models.functions import Length

from openzaak.utils.db import pg_advisory_lock

from .identification import ZaakIdentificatie

LOCK_ID_IDENTIFICATION_GENERATION = "generate-zaak-identification"


class BaseZaakIdentificatie(ABC):
    model = ZaakIdentificatie

    def __init__(self, bronorganisatie: str, **kwargs):
        self.bronorganisatie = bronorganisatie

    @abstractmethod
    def current(self) -> str:
        pass

    @abstractmethod
    def _sequence(self, current_identificatie: str) -> Generator[str, None, None]:
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
                identificatie=next(self._sequence(self.current())),
                bronorganisatie=self.bronorganisatie,
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
            return self.model.objects.bulk_create(
                self.model(identificatie=id, bronorganisatie=self.bronorganisatie)
                for id in islice(self._sequence(self.current()), amount)
            )


class YearIdentification(BaseZaakIdentificatie):
    def __init__(self, bronorganisatie: str, date: date, **kwargs):
        super().__init__(bronorganisatie, **kwargs)

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

    def _sequence(self, current_identificatie: str) -> Generator[str, None, None]:
        number = int(current_identificatie.split("-")[-1])
        while True:
            number += 1
            yield f"{self.prefix}-{str(number).zfill(10)}"


class CreationYearIdentification(YearIdentification):
    def __init__(self, bronorganisatie: str, **kwargs):
        super().__init__(bronorganisatie, date.today(), **kwargs)


class StartDatumYearIdentification(YearIdentification):
    def __init__(self, bronorganisatie: str, startdatum: date, **kwargs):
        super().__init__(bronorganisatie, startdatum, **kwargs)


class UWVIdentification(BaseZaakIdentificatie):
    """
    Custom zaak identification for UWV

    A00000000 -> Z99999999 -> AA99999999 -> AB99999999 -> AZ99999999 -> BA99999999 -> ZZ99999999

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

        return max_id or "A00000000"

    def _as_int(self, char: str) -> int:
        return int(char) if char.isnumeric() else (ord(char) - 65)

    def _next_prefix(self, prefix: str) -> str:
        # convert to int (base 26 bijective)
        n = 0
        for char in prefix:
            # 64: A->1
            n = n * 26 + (ord(char) - 64)

        # next
        n += 1

        # convert back to str
        res = []
        while n > 0:
            n -= 1  # bijective! (A=1, not A=0)
            res.append(chr((n % 26) + 65))  # 65 is 'A'
            n //= 26

        return "".join(reversed(res))

    def _calc_checksum(self, prefix: str, seq: str):
        """
        valid identifier is by definition:
            weighted_sum + checksum × w ≡ 10 (mod 11)
        algebra:
            checksum × w = 10 − weighted_sum (mod 11)
            checksum = (10 − weighted_sum) * w⁻¹ (mod 11)
        """

        values = map(self._as_int, chain(prefix, seq))
        weights = count(1)
        weighted_sum = sum(starmap(mul, zip(values, weights)))
        w = next(weights)  # weight of the checksum digit identifier[-1]

        # This pow breaks when w is not co-prime to 11. 11 is prime so ValueError
        # is raised if w is a multiple of 11. But max len of an id is 2 + 8, and
        # we checked for len(next_prefix), so w < 11 always holds.
        checksum = ((10 - weighted_sum) * pow(w, -1, 11)) % 11
        return checksum

    def _sequence(self, current_identificatie: str) -> Generator[str, None, None]:
        if current_identificatie == "A00000000":
            # special case for initial identification
            current_identificatie = "A00000006"
            yield current_identificatie

        prefix = current_identificatie.strip("0123456789")
        # sequence number without elf proef checksum
        seq = current_identificatie[len(prefix) : len(prefix) + 7]

        while True:
            if seq == "9999999":
                seq = f"{0:07n}"
                prefix = self._next_prefix(prefix)
            else:
                seq = f"{int(seq) + 1:07d}"

            if len(prefix) > 2:
                raise ValueError("Max identification reached")

            checksum = self._calc_checksum(prefix, seq)

            if checksum != 10:
                # we need a single digit checksum
                # if 10 calculate next
                yield f"{prefix}{seq}{checksum}"


def get_base_identification_class():
    match settings.ZAAK_IDENTIFICATIE_GENERATOR:
        case "use-uwv-identification":
            identification_class = UWVIdentification
        case _:
            identification_class = YearIdentification

    return identification_class
