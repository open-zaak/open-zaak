import logging
import uuid as _uuid

from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.fields import FkOrURLField
from privates.fields import PrivateMediaFileField
from vng_api_common.constants import ObjectTypes
from vng_api_common.descriptors import GegevensGroepType
from vng_api_common.fields import RSINField, VertrouwelijkheidsAanduidingField
from vng_api_common.models import APIMixin
from vng_api_common.utils import generate_unique_identification
from vng_api_common.validators import alphanumeric_excluding_diacritic

from openzaak.utils.mixins import AuditTrailMixin

from .constants import ChecksumAlgoritmes, OndertekeningSoorten, Statussen
from .query import (
    InformatieobjectQuerySet,
    InformatieobjectRelatedQuerySet,
    ObjectInformatieObjectQuerySet,
)
from .validators import validate_status

logger = logging.getLogger(__name__)

__all__ = [
    "InformatieObject",
    "EnkelvoudigInformatieObjectCanonical",
    "EnkelvoudigInformatieObject",
    "Gebruiksrechten",
    "ObjectInformatieObject",
]


class InformatieObject(models.Model):
    identificatie = models.CharField(
        max_length=40,
        validators=[alphanumeric_excluding_diacritic],
        blank=True,
        default="",
        help_text="Een binnen een gegeven context ondubbelzinnige referentie "
        "naar het INFORMATIEOBJECT.",
        db_index=True,
    )
    bronorganisatie = RSINField(
        max_length=9,
        help_text="Het RSIN van de Niet-natuurlijk persoon zijnde de "
        "organisatie die het informatieobject heeft gecreëerd of "
        "heeft ontvangen en als eerste in een samenwerkingsketen "
        "heeft vastgelegd.",
        db_index=True,
    )
    # TODO: change to read-only?
    creatiedatum = models.DateField(
        help_text="Een datum of een gebeurtenis in de levenscyclus van het "
        "INFORMATIEOBJECT."
    )
    titel = models.CharField(
        max_length=200,
        help_text="De naam waaronder het INFORMATIEOBJECT formeel bekend is.",
    )
    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        blank=True,
        help_text="Aanduiding van de mate waarin het INFORMATIEOBJECT voor de "
        "openbaarheid bestemd is.",
    )
    auteur = models.CharField(
        max_length=200,
        help_text="De persoon of organisatie die in de eerste plaats "
        "verantwoordelijk is voor het creëren van de inhoud van het "
        "INFORMATIEOBJECT.",
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        blank=True,
        choices=Statussen.choices,
        help_text=_(
            "Aanduiding van de stand van zaken van een INFORMATIEOBJECT. "
            "De waarden 'in bewerking' en 'ter vaststelling' komen niet "
            "voor als het attribuut `ontvangstdatum` van een waarde is voorzien. "
            "Wijziging van de Status in 'gearchiveerd' impliceert dat "
            "het informatieobject een duurzaam, niet-wijzigbaar Formaat dient te hebben."
        ),
    )
    beschrijving = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Een generieke beschrijving van de inhoud van het "
        "INFORMATIEOBJECT.",
    )
    ontvangstdatum = models.DateField(
        _("ontvangstdatum"),
        null=True,
        blank=True,
        help_text=_(
            "De datum waarop het INFORMATIEOBJECT ontvangen is. Verplicht "
            "te registreren voor INFORMATIEOBJECTen die van buiten de "
            "zaakbehandelende organisatie(s) ontvangen zijn. "
            "Ontvangst en verzending is voorbehouden aan documenten die "
            "van of naar andere personen ontvangen of verzonden zijn "
            "waarbij die personen niet deel uit maken van de behandeling "
            "van de zaak waarin het document een rol speelt."
        ),
    )
    verzenddatum = models.DateField(
        _("verzenddatum"),
        null=True,
        blank=True,
        help_text=_(
            "De datum waarop het INFORMATIEOBJECT verzonden is, zoals "
            "deze op het INFORMATIEOBJECT vermeld is. Dit geldt voor zowel "
            "inkomende als uitgaande INFORMATIEOBJECTen. Eenzelfde "
            "informatieobject kan niet tegelijk inkomend en uitgaand zijn. "
            "Ontvangst en verzending is voorbehouden aan documenten die "
            "van of naar andere personen ontvangen of verzonden zijn "
            "waarbij die personen niet deel uit maken van de behandeling "
            "van de zaak waarin het document een rol speelt."
        ),
    )
    indicatie_gebruiksrecht = models.NullBooleanField(
        _("indicatie gebruiksrecht"),
        blank=True,
        default=None,
        help_text=_(
            "Indicatie of er beperkingen gelden aangaande het gebruik van "
            "het informatieobject anders dan raadpleging. Dit veld mag "
            "`null` zijn om aan te geven dat de indicatie nog niet bekend is. "
            "Als de indicatie gezet is, dan kan je de gebruiksrechten die "
            "van toepassing zijn raadplegen via de GEBRUIKSRECHTen resource."
        ),
    )

    # signing in some sort of way
    # TODO: De attribuutsoort mag niet van een waarde zijn voorzien
    # als de attribuutsoort ?Status? de waarde ?in bewerking?
    # of ?ter vaststelling? heeft.
    ondertekening_soort = models.CharField(
        _("ondertekeningsoort"),
        max_length=10,
        blank=True,
        choices=OndertekeningSoorten.choices,
        help_text=_(
            "Aanduiding van de wijze van ondertekening van het INFORMATIEOBJECT"
        ),
    )
    ondertekening_datum = models.DateField(
        _("ondertekeningdatum"),
        blank=True,
        null=True,
        help_text=_(
            "De datum waarop de ondertekening van het INFORMATIEOBJECT heeft plaatsgevonden."
        ),
    )

    _informatieobjecttype_url = models.URLField(
        _("extern informatieobjecttype"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern INFORMATIEOBJECTTYPE (in een andere Catalogi API)."
        ),
    )
    _informatieobjecttype = models.ForeignKey(
        "catalogi.InformatieObjectType",
        on_delete=models.CASCADE,
        help_text=_(
            "URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API)."
        ),
        null=True,
        blank=True,
    )
    informatieobjecttype = FkOrURLField(
        fk_field="_informatieobjecttype",
        url_field="_informatieobjecttype_url",
        help_text="URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API).",
    )

    objects = InformatieobjectQuerySet.as_manager()

    IDENTIFICATIE_PREFIX = "DOCUMENT"

    class Meta:
        verbose_name = "informatieobject"
        verbose_name_plural = "informatieobject"
        unique_together = ("bronorganisatie", "identificatie")
        abstract = True

    def __str__(self) -> str:
        return self.identificatie

    def save(self, *args, **kwargs):
        if not self.identificatie:
            self.identificatie = generate_unique_identification(self, "creatiedatum")
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        validate_status(
            status=self.status, ontvangstdatum=self.ontvangstdatum, instance=self
        )

    ondertekening = GegevensGroepType(
        {"soort": ondertekening_soort, "datum": ondertekening_datum}
    )

    def unique_representation(self):
        return f"{self.bronorganisatie} - {self.identificatie}"


class EnkelvoudigInformatieObjectCanonical(models.Model):
    """
    Indicates the identity of a document
    """

    lock = models.CharField(
        default="",
        blank=True,
        max_length=100,
        help_text="Hash string, wordt gebruikt als ID voor de lock",
    )

    def __str__(self):
        return str(self.latest_version)

    @property
    def latest_version(self):
        # there is implicit sorting by versie desc in EnkelvoudigInformatieObject.Meta.ordering
        versies = self.enkelvoudiginformatieobject_set.all()
        return versies.first()


class EnkelvoudigInformatieObject(AuditTrailMixin, APIMixin, InformatieObject):
    """
    Stores the content of a specific version of an
    EnkelvoudigInformatieObjectCanonical

    The model is split into two parts to support versioning, now a single
    `EnkelvoudigInformatieObjectCanonical` can exist with multiple different
    `EnkelvoudigInformatieObject`s, which can be retrieved by filtering
    """

    canonical = models.ForeignKey(
        EnkelvoudigInformatieObjectCanonical, on_delete=models.CASCADE
    )
    uuid = models.UUIDField(
        default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )

    # NOTE: Don't validate but rely on externally maintened list of Media Types
    # and that consumers know what they're doing. This prevents updating the
    # API specification on every Media Type that is added.
    formaat = models.CharField(
        max_length=255,
        blank=True,
        help_text='Het "Media Type" (voorheen "MIME type") voor de wijze waarop'
        "de inhoud van het INFORMATIEOBJECT is vastgelegd in een "
        "computerbestand. Voorbeeld: `application/msword`. Zie: "
        "https://www.iana.org/assignments/media-types/media-types.xhtml",
    )
    taal = models.CharField(
        max_length=3,
        help_text="Een ISO 639-2/B taalcode waarin de inhoud van het "
        "INFORMATIEOBJECT is vastgelegd. Voorbeeld: `nld`. Zie: "
        "https://www.iso.org/standard/4767.html",
    )

    bestandsnaam = models.CharField(
        _("bestandsnaam"),
        max_length=255,
        blank=True,
        help_text=_(
            "De naam van het fysieke bestand waarin de inhoud van het "
            "informatieobject is vastgelegd, inclusief extensie."
        ),
    )
    inhoud = PrivateMediaFileField(upload_to="uploads/%Y/%m/")
    # inhoud = models.FileField(upload_to='uploads/%Y/%m/')
    link = models.URLField(
        max_length=200,
        blank=True,
        help_text="De URL waarmee de inhoud van het INFORMATIEOBJECT op te "
        "vragen is.",
    )

    # these fields should not be modified directly, but go through the `integriteit` descriptor
    integriteit_algoritme = models.CharField(
        _("integriteit algoritme"),
        max_length=20,
        choices=ChecksumAlgoritmes.choices,
        blank=True,
        help_text=_("Aanduiding van algoritme, gebruikt om de checksum te maken."),
    )
    integriteit_waarde = models.CharField(
        _("integriteit waarde"),
        max_length=128,
        blank=True,
        help_text=_("De waarde van de checksum."),
    )
    integriteit_datum = models.DateField(
        _("integriteit datum"),
        null=True,
        blank=True,
        help_text=_("Datum waarop de checksum is gemaakt."),
    )

    integriteit = GegevensGroepType(
        {
            "algoritme": integriteit_algoritme,
            "waarde": integriteit_waarde,
            "datum": integriteit_datum,
        }
    )

    versie = models.PositiveIntegerField(
        default=1,
        help_text=_(
            "Het (automatische) versienummer van het INFORMATIEOBJECT. Deze begint bij 1 als het "
            "INFORMATIEOBJECT aangemaakt wordt."
        ),
    )
    begin_registratie = models.DateTimeField(
        auto_now=True,
        help_text=_(
            "Een datumtijd in ISO8601 formaat waarop deze versie van het INFORMATIEOBJECT is aangemaakt of "
            "gewijzigd."
        ),
        db_index=True,
    )

    _locked = False

    class Meta:
        unique_together = ("uuid", "versie")
        verbose_name = _("Document")
        verbose_name_plural = _("Documenten")
        indexes = [models.Index(fields=["canonical", "-versie"])]
        ordering = ["canonical", "-versie"]

    def _get_locked(self) -> bool:
        if self.pk:
            return bool(self.canonical.lock)
        return self._locked

    def _set_locked(self, value: bool) -> None:
        self._locked = value

    locked = property(_get_locked, _set_locked)


class Gebruiksrechten(models.Model):
    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    informatieobject = models.ForeignKey(
        "EnkelvoudigInformatieObjectCanonical",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het INFORMATIEOBJECT.",
    )
    omschrijving_voorwaarden = models.TextField(
        _("omschrijving voorwaarden"),
        help_text=_(
            "Omschrijving van de van toepassing zijnde voorwaarden aan "
            "het gebruik anders dan raadpleging"
        ),
    )
    startdatum = models.DateTimeField(
        _("startdatum"),
        help_text=_(
            "Begindatum van de periode waarin de gebruiksrechtvoorwaarden van toepassing zijn. "
            "Doorgaans is de datum van creatie van het informatieobject de startdatum."
        ),
        db_index=True,
    )
    einddatum = models.DateTimeField(
        _("startdatum"),
        blank=True,
        null=True,
        help_text=_(
            "Einddatum van de periode waarin de gebruiksrechtvoorwaarden van toepassing zijn."
        ),
        db_index=True,
    )

    objects = InformatieobjectRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = _("gebruiksrecht informatieobject")
        verbose_name_plural = _("gebruiksrechten informatieobject")

    def __str__(self):
        return str(self.informatieobject.latest_version)

    @transaction.atomic
    def save(self, *args, **kwargs):
        informatieobject_versie = self.informatieobject.latest_version
        # ensure the indication is set properly on the IO
        if not informatieobject_versie.indicatie_gebruiksrecht:
            informatieobject_versie.indicatie_gebruiksrecht = True
            informatieobject_versie.save()
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        informatieobject = self.informatieobject
        other_gebruiksrechten = informatieobject.gebruiksrechten_set.exclude(pk=self.pk)
        if not other_gebruiksrechten.exists():
            informatieobject_versie = self.informatieobject.latest_version
            informatieobject_versie.indicatie_gebruiksrecht = None
            informatieobject_versie.save()

    def unique_representation(self):
        informatieobject = self.informatieobject.latest_version
        return f"({informatieobject.unique_representation()}) - {self.omschrijving_voorwaarden[:50]}"


class ObjectInformatieObject(models.Model):
    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    informatieobject = models.ForeignKey(
        "EnkelvoudigInformatieObjectCanonical",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het INFORMATIEOBJECT.",
    )

    # meta-info about relation
    object_type = models.CharField(
        "objecttype",
        max_length=100,
        choices=ObjectTypes.choices,
        help_text="Het type van het gerelateerde OBJECT.",
    )

    # relations to the possible other objects
    _zaak_url = models.URLField(_("extern zaak"), blank=True, max_length=1000)
    _zaak = models.ForeignKey(
        "zaken.Zaak", on_delete=models.CASCADE, null=True, blank=True
    )
    zaak = FkOrURLField(fk_field="_zaak", url_field="_zaak_url", blank=True, null=True,)

    _besluit_url = models.URLField(_("extern besluit"), blank=True, max_length=1000)
    _besluit = models.ForeignKey(
        "besluiten.Besluit", on_delete=models.CASCADE, null=True, blank=True
    )
    besluit = FkOrURLField(
        fk_field="_besluit", url_field="_besluit_url", blank=True, null=True,
    )

    objects = ObjectInformatieObjectQuerySet.as_manager()

    class Meta:
        verbose_name = _("objectinformatieobject")
        verbose_name_plural = _("objectinformatieobjecten")
        # check that only one loose-fk field (fk or url) is filled
        constraints = [
            models.CheckConstraint(
                check=Q(
                    Q(_zaak_url="", _zaak__isnull=False)
                    | Q(~Q(_zaak_url=""), _zaak__isnull=True),
                    object_type=ObjectTypes.zaak,
                    _besluit__isnull=True,
                    _besluit_url="",
                )
                | Q(
                    Q(_besluit_url="", _besluit__isnull=False)
                    | Q(~Q(_besluit_url=""), _besluit__isnull=True),
                    object_type=ObjectTypes.besluit,
                    _zaak__isnull=True,
                    _zaak_url="",
                ),
                name="check_type",
            ),
            models.UniqueConstraint(
                fields=("informatieobject", "_zaak"), name="unique_io_zaak_local"
            ),
            models.UniqueConstraint(
                fields=("informatieobject", "_zaak_url"),
                name="unique_io_zaak_external",
                condition=~Q(_zaak_url=""),
            ),
            models.UniqueConstraint(
                fields=("informatieobject", "_besluit"), name="unique_io_besluit_local"
            ),
            models.UniqueConstraint(
                fields=("informatieobject", "_besluit_url"),
                name="unique_io_besluit_external",
                condition=~Q(_besluit_url=""),
            ),
        ]

    def __str__(self):
        return _("Relation between {document} and {object}").format(
            document=self.informatieobject, object=self.object
        )

    @property
    def object(self) -> models.Model:
        return getattr(self, self.object_type)

    def unique_representation(self):
        io_id = self.object.identificatie
        return f"({self.informatieobject.latest_version.unique_representation()}) - {io_id}"
