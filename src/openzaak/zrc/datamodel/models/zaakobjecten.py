import logging

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from ..constants import (
    TyperingInrichtingselement, TyperingKunstwerk, TyperingWater,
    TypeSpoorbaan
)
from .core import ZaakObject

logger = logging.getLogger(__name__)

__all__ = [
    "Buurt",
    "Gemeente",
    "GemeentelijkeOpenbareRuimte",
    "Huishouden",
    "Inrichtingselement",
    "Kunstwerkdeel",
    "MaatschappelijkeActiviteit",
    "OpenbareRuimte",
    "Pand",
    "Spoorbaandeel",
    "Terreindeel",
    "Waterdeel",
    "Wegdeel",
    "Wijk",
    "Woonplaats",
    "Overige",
    "TerreinGebouwdObject",
    "WozDeelobject",
    "WozWaarde",
    "WozObject",
    "ZakelijkRecht",
    "KadastraleOnroerendeZaak",
    "ZakelijkRechtHeeftAlsGerechtigde",
    "Adres",
]


class Buurt(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    buurt_code = models.CharField(
        max_length=2, help_text='De code behorende bij de naam van de buurt'
    )
    buurt_naam = models.CharField(
        max_length=40, help_text='De naam van de buurt, zoals die door het CBS wordt gebruikt.'
    )
    gem_gemeente_code = models.CharField(
        max_length=4, help_text='Een numerieke aanduiding waarmee een Nederlandse gemeente uniek wordt aangeduid'
    )
    wyk_wijk_code = models.CharField(
        max_length=2, help_text='De code behorende bij de naam van de wijk'
    )

    class Meta:
        unique_together = ('buurt_code', 'wyk_wijk_code')


class Gemeente(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    gemeente_naam = models.CharField(
        max_length=80, help_text='De officiële door de gemeente vastgestelde gemeentenaam.'
    )
    gemeente_code = models.CharField(
        max_length=4, help_text='Een numerieke aanduiding waarmee een Nederlandse gemeente uniek wordt aangeduid'
    )


class GemeentelijkeOpenbareRuimte(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    openbare_ruimte_naam = models.CharField(
        max_length=80, help_text='Een door het bevoegde gemeentelijke orgaan aan een '
                                 'OPENBARE RUIMTE toegekende benaming'
    )


class Huishouden(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    nummer = models.CharField(
        max_length=12, help_text='Uniek identificerend administratienummer van een huishouden '
                                 'zoals toegekend door de gemeente waarin het huishouden woonachtig is.')


class Inrichtingselement(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=30, choices=TyperingInrichtingselement.choices,
        help_text='Specificatie van de aard van het inrichtingselement.'
    )
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    naam = models.TextField(
        max_length=500, blank=True, help_text='De benaming van het OBJECT'
    )


class Kunstwerkdeel(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=40, choices=TyperingKunstwerk.choices,
        help_text='Specificatie van het soort Kunstwerk waartoe het kunstwerkdeel behoort.')
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    naam = models.CharField(max_length=80)


class MaatschappelijkeActiviteit(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    kvk_nummer = models.CharField(
        max_length=8, help_text='Landelijk uniek identificerend administratienummer van een '
                                'MAATSCHAPPELIJKE ACTIVITEIT zoals toegewezen door de Kamer van Koophandel (KvK).'
    )
    handelsnaam = models.CharField(
        max_length=200, help_text='De naam waaronder de onderneming handelt.'
    )


class OpenbareRuimte(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    wpl_woonplaats_naam = models.CharField(max_length=80)
    gor_openbare_ruimte_naam = models.CharField(
        max_length=80, help_text='Een door het bevoegde gemeentelijke orgaan aan een '
                                 'OPENBARE RUIMTE toegekende benaming'
    )


class Pand(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )


class Spoorbaandeel(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=40, choices=TypeSpoorbaan.choices, help_text='Specificatie van het soort Spoorbaan'
    )
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    naam = models.TextField(
        max_length=500, blank=True, help_text='De benaming van het OBJECT'
    )


class Terreindeel(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=40
    )
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    naam = models.TextField(
        max_length=500, blank=True, help_text='De benaming van het OBJECT'
    )


class Waterdeel(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    type_waterdeel = models.CharField(
        max_length=50, choices=TyperingWater.choices,
        help_text='Specificatie van het soort water')

    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    naam = models.TextField(
        max_length=500, blank=True, help_text='De benaming van het OBJECT'
    )


class Wegdeel(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    naam = models.TextField(
        max_length=500, blank=True, help_text='De benaming van het OBJECT'
    )


class Wijk(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    wijk_code = models.CharField(
        max_length=2, help_text='De code behorende bij de naam van de wijk.'
    )
    wijk_naam = models.CharField(
        max_length=40, help_text='De naam van de wijk, zoals die door het CBS wordt gebruikt.'
    )
    gem_gemeente_code = models.CharField(
        max_length=4, help_text='Een numerieke aanduiding waarmee een Nederlandse gemeente uniek wordt aangeduid'
    )


class Woonplaats(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    woonplaats_naam = models.CharField(
        max_length=80, help_text='De door het bevoegde gemeentelijke orgaan aan een WOONPLAATS toegekende benaming.'
    )


class Overige(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    overige_data = JSONField()


class TerreinGebouwdObject(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE, null=True)
    huishouden = models.OneToOneField(Huishouden, on_delete=models.CASCADE, null=True, related_name='is_gehuisvest_in')
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )

    def clean(self):
        super().clean()
        if self.zaakobject is None and self.huishouden is None:
            raise ValidationError('Relations to ZaakObject or Huishouden models should be set')


class WozDeelobject(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    nummer_woz_deel_object = models.CharField(
        max_length=6, help_text='Uniek identificatienummer voor het deelobject binnen een WOZ-object.')


class WozWaarde(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    waardepeildatum = models.CharField(
        max_length=9, help_text='De datum waarnaar de waarde van het WOZ-object wordt bepaald.'
    )


class WozObject(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE, null=True)
    woz_deelobject = models.OneToOneField(
        WozDeelobject, on_delete=models.CASCADE, null=True, related_name='is_onderdeel_van'
    )
    woz_warde = models.OneToOneField(
        WozWaarde, on_delete=models.CASCADE, null=True, related_name='is_voor'
    )
    woz_object_nummer = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )

    def clean(self):
        super().clean()
        if self.zaakobject is None and self.woz_deelobject is None and self.woz_warde is None:
            raise ValidationError('Relations to ZaakObject, WozDeelobject or WozWaarde models should be set')


class ZakelijkRecht(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE)
    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    avg_aard = models.CharField(
        max_length=1000, help_text='aanduiding voor de aard van het recht'
    )


class KadastraleOnroerendeZaak(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE, null=True)
    zakelijk_recht = models.OneToOneField(
        ZakelijkRecht, on_delete=models.CASCADE, null=True, related_name='heeft_betrekking_op'
    )
    kadastrale_identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    kadastrale_aanduiding = models.CharField(
        max_length=1000, help_text='De typering van de kadastrale aanduiding van een onroerende zaak conform Kadaster'
    )

    def clean(self):
        super().clean()
        if self.zaakobject is None and self.zakelijk_recht is None :
            raise ValidationError('Relations to ZaakObject or ZakelijkRecht models should be set')


class ZakelijkRechtHeeftAlsGerechtigde(models.Model):
    zakelijk_recht = models.OneToOneField(ZakelijkRecht, on_delete=models.CASCADE, related_name='heeft_als_gerechtigde')


class Adres(models.Model):
    zaakobject = models.OneToOneField(ZaakObject, on_delete=models.CASCADE, null=True)
    natuurlijkpersoon = models.OneToOneField(
        'datamodel.NatuurlijkPersoon', on_delete=models.CASCADE, null=True, related_name='verblijfsadres'
    )
    vestiging = models.OneToOneField(
        'datamodel.Vestiging', on_delete=models.CASCADE, null=True, related_name='verblijfsadres'
    )
    wozobject = models.OneToOneField(
        WozObject, on_delete=models.CASCADE, null=True, related_name='aanduiding_woz_object'
    )
    terreingebouwdobject = models.OneToOneField(
        TerreinGebouwdObject, on_delete=models.CASCADE, null=True, related_name='adres_aanduiding_grp'
    )

    identificatie = models.CharField(
        max_length=100, help_text='De unieke identificatie van het OBJECT'
    )
    wpl_woonplaats_naam = models.CharField(max_length=80)
    gor_openbare_ruimte_naam = models.CharField(
        max_length=80, help_text='Een door het bevoegde gemeentelijke orgaan aan een '
                                 'OPENBARE RUIMTE toegekende benaming'
    )
    huisnummer = models.PositiveIntegerField(validators=[MaxValueValidator(99999)])
    huisletter = models.CharField(max_length=1, blank=True)
    huisnummertoevoeging = models.CharField(max_length=4, blank=True)
    postcode = models.CharField(max_length=7, blank=True)

    num_identificatie = models.CharField(max_length=100, blank=True)
    locatie_omschrijving = models.CharField(max_length=1000, blank=True)
    locatie_aanduiding = models.CharField(max_length=100, blank=True)

    def clean(self):
        super().clean()
        if self.zaakobject is None and self.wozobject is None and self.terreingebouwdobject is None \
                and self.natuurlijkpersoon is None and self.vestiging is None:
            raise ValidationError('Relations to ZaakObject, WozObject, NatuurlijkPersoon, '
                                  'Vestiging or TerreinGebouwdObject models should be set')
