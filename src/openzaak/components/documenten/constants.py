# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Dict

from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common import constants
from vng_api_common.choices import TextChoicesWithDescriptions


class Statussen(TextChoicesWithDescriptions):
    in_bewerking = "in_bewerking", _("In bewerking")
    ter_vaststelling = "ter_vaststelling", _("Ter vaststelling")
    definitief = "definitief", _("Definitief")
    gearchiveerd = "gearchiveerd", _("Gearchiveerd")

    @classmethod
    def invalid_for_received(cls) -> tuple:
        return cls.in_bewerking, cls.ter_vaststelling

    @classmethod
    def descriptions(cls) -> Dict[str, str]:
        return {
            cls.in_bewerking: _("Aan het informatieobject wordt nog gewerkt."),
            cls.ter_vaststelling: _(
                "Informatieobject gereed maar moet nog vastgesteld " "worden."
            ),
            cls.definitief: _(
                "Informatieobject door bevoegd iets of iemand vastgesteld dan wel ontvangen."
            ),
            cls.gearchiveerd: _(
                "Informatieobject duurzaam bewaarbaar gemaakt; een gearchiveerd informatie-element."
            ),
        }


class ChecksumAlgoritmes(models.TextChoices):
    crc_16 = "crc_16", _("CRC-16")
    crc_32 = "crc_32", _("CRC-32")
    crc_64 = "crc_64", _("CRC-64")
    fletcher_4 = "fletcher_4", _("Fletcher-4")
    fletcher_8 = "fletcher_8", _("Fletcher-8")
    fletcher_16 = "fletcher_16", _("Fletcher-16")
    fletcher_32 = "fletcher_32", _("Fletcher-32")
    hmac = "hmac", _("HMAC")
    md5 = "md5", _("MD5")
    sha_1 = "sha_1", _("SHA-1")
    sha_256 = "sha_256", _("SHA-256")
    sha_512 = "sha_512", _("SHA-512")
    sha_3 = "sha_3", _("SHA-3")


class OndertekeningSoorten(models.TextChoices):
    analoog = "analoog", _("Analoog")
    digitaal = "digitaal", _("Digitaal")
    pki = "pki", _("PKI")
    # TODO: more...


class ObjectInformatieObjectTypes(models.TextChoices):
    besluit = constants.BESLUIT_CHOICE
    zaak = constants.ZAAK_CHOICE
    verzoek = constants.VERZOEK_CHOICE


class AfzenderTypes(models.TextChoices):
    afzender = "afzender", _("Afzender")
    geadresseerde = "geadresseerde", _("Geadresseerde")


class PostAdresTypes(models.TextChoices):
    antwoordnummer = "antwoordnummer", _("Antwoordnummer")
    postbusnummer = "postbusnummer", _("Postbusnummer")
