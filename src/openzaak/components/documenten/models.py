# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import uuid as _uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _

from drc_cmis.utils import exceptions
from drc_cmis.utils.convert import make_absolute_uri
from privates.fields import PrivateMediaFileField
from rest_framework.reverse import reverse
from vng_api_common.descriptors import GegevensGroepType
from vng_api_common.fields import RSINField, VertrouwelijkheidsAanduidingField
from vng_api_common.utils import generate_unique_identification
from zgw_consumers.models import ServiceUrlField

from openzaak.utils.fields import (
    AliasServiceUrlField,
    FkOrServiceUrlField,
    NLPostcodeField,
    RelativeURLField,
    ServiceFkField,
)
from openzaak.utils.mixins import APIMixin, AuditTrailMixin, CMISClientMixin

from ..besluiten.models import BesluitInformatieObject
from ..zaken.models import ZaakInformatieObject
from .caching import CMISETagMixin
from .constants import (
    AfzenderTypes,
    ChecksumAlgoritmes,
    ObjectInformatieObjectTypes,
    OndertekeningSoorten,
    PostAdresTypes,
    Statussen,
)
from .managers import (
    AdapterManager,
    GebruiksrechtenAdapterManager,
    ObjectInformatieObjectAdapterManager,
)
from .query.django import (
    BestandsDeelQuerySet,
    InformatieobjectQuerySet,
    InformatieobjectRelatedQuerySet,
)
from .utils import private_media_storage_cmis
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
    indicatie_gebruiksrecht = models.BooleanField(
        _("indicatie gebruiksrecht"),
        blank=True,
        null=True,
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

    _informatieobjecttype_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern INFORMATIEOBJECTTYPE (in een andere Catalogi API).",
    )
    _informatieobjecttype_relative_url = RelativeURLField(
        _("informatieobjecttype relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern INFORMATIEOBJECTTYPE (in een andere Catalogi API).",
    )
    _informatieobjecttype_url = ServiceUrlField(
        base_field="_informatieobjecttype_base_url",
        relative_field="_informatieobjecttype_relative_url",
        verbose_name=_("extern informatieobjecttype"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern INFORMATIEOBJECTTYPE (in een andere Catalogi API)."
        ),
    )
    _informatieobjecttype = models.ForeignKey(
        "catalogi.InformatieObjectType",
        on_delete=models.PROTECT,
        help_text=_(
            "URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API)."
        ),
        null=True,
        blank=True,
    )
    informatieobjecttype = FkOrServiceUrlField(
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


class EnkelvoudigInformatieObjectCanonical(models.Model, CMISClientMixin):
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
        if settings.CMIS_ENABLED:
            return "(virtual canonical instance)"
        return str(self.latest_version)

    @property
    def latest_version(self):
        if settings.CMIS_ENABLED:
            raise RecursionError(
                "Using latest_version() with CMIS enabled causes an infinite loop."
            )
        # there is implicit sorting by versie desc in EnkelvoudigInformatieObject.Meta.ordering
        versies = self.enkelvoudiginformatieobject_set.all()
        return versies.first()

    def save(self, *args, **kwargs) -> None:
        if settings.CMIS_ENABLED:
            return
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if settings.CMIS_ENABLED:
            return
        super().delete(*args, **kwargs)

    def lock_document(self, doc_uuid: str) -> None:
        lock = _uuid.uuid4().hex
        if settings.CMIS_ENABLED:
            self.cmis_client.lock_document(doc_uuid, lock)
        self.lock = lock

    def unlock_document(self, doc_uuid, lock, force_unlock=False):
        if settings.CMIS_ENABLED:
            self.cmis_client.unlock_document(
                drc_uuid=doc_uuid, lock=lock, force=force_unlock
            )
        self.lock = ""


class EnkelvoudigInformatieObject(
    CMISETagMixin, AuditTrailMixin, APIMixin, InformatieObject, CMISClientMixin
):
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
        "INFORMATIEOBJECT is vastgelegd. Voorbeeld: `dut`. Zie: "
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

    bestandsomvang = models.PositiveBigIntegerField(
        _("bestandsomvang"),
        null=True,
        help_text=_("Aantal bytes dat de inhoud van INFORMATIEOBJECT in beslag neemt."),
    )
    inhoud = PrivateMediaFileField(
        upload_to="uploads/%Y/%m/", storage=private_media_storage_cmis
    )
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
    verschijningsvorm = models.TextField(
        blank=True,
        help_text=_("De essentiële opmaakaspecten van een INFORMATIEOBJECT."),
    )

    trefwoorden = ArrayField(
        models.CharField(_("trefwoord"), max_length=100),
        blank=True,
        default=list,
        help_text=_("Een lijst van trefwoorden gescheiden door comma's."),
        db_index=True,
    )

    # When dealing with remote EIO, there is no pk or canonical instance to derive
    # the lock status from. The getters and setters then use this private attribute.
    _locked = False
    _bestandsomvang = None
    objects = AdapterManager()

    class Meta:
        # No bronorganisatie/identificatie unique-together constraint, otherwise new versions of a document cannot be
        # saved to the database.
        unique_together = [("uuid", "versie")]
        verbose_name = _("Document")
        verbose_name_plural = _("Documenten")
        indexes = [models.Index(fields=["canonical", "-versie"])]
        ordering = ["canonical", "-versie"]

    def __init__(self, *args, **kwargs):
        kwargs.pop("_request", None)  # see hacky workaround in EIOSerializer.create
        super().__init__(*args, **kwargs)

    # Since canonicals are not stored in the database for CMIS, the BestandsDelen must
    # be retrieved by using the UUID
    def get_bestandsdelen(self):
        if settings.CMIS_ENABLED:
            bestandsdelen = BestandsDeel.objects.filter(informatieobject_uuid=self.uuid)
        else:
            bestandsdelen = self.canonical.bestandsdelen
        return bestandsdelen

    @property
    def locked(self) -> bool:
        if self.pk or self.canonical is not None:
            return bool(self.canonical.lock)
        return self._locked

    @locked.setter
    def locked(self, value: bool) -> None:
        # this should only be called for remote objects, as other objects derive the
        # lock status from the canonical object
        assert self.canonical is None, "Setter should only be called for remote objects"
        self._locked = value

    def save(self, *args, **kwargs) -> None:
        if not settings.CMIS_ENABLED:
            return super().save(*args, **kwargs)
        else:
            model_data = model_to_dict(self)
            # If the document doesn't exist, create it, otherwise update it
            try:
                # sanity - check - assert the doc exists in CMIS backend
                self.cmis_client.get_document(drc_uuid=self.uuid)
                # update the instance state to the storage backend
                EnkelvoudigInformatieObject.objects.filter(uuid=self.uuid).update(
                    **model_data
                )
                # Needed or the current django object will contain the version number and the download url
                # from before the update and this data is sent back in the response
                modified_document = EnkelvoudigInformatieObject.objects.get(
                    uuid=self.uuid
                )
                self.versie = modified_document.versie
                self.inhoud = modified_document.inhoud
            except exceptions.DocumentDoesNotExistError:
                EnkelvoudigInformatieObject.objects.create(**model_data)

    def delete(self, *args, **kwargs):
        if not settings.CMIS_ENABLED:
            return super().delete(*args, **kwargs)
        else:
            if self.has_gebruiksrechten():
                eio_instance_url = self.get_url()
                gebruiksrechten = Gebruiksrechten.objects.filter(
                    informatieobject=eio_instance_url
                )
                for gebruiksrechten_doc in gebruiksrechten:
                    gebruiksrechten_doc.delete()
            self.cmis_client.delete_document(self.uuid)

    def destroy(self):
        if settings.CMIS_ENABLED:
            self.delete()
        else:
            self.canonical.delete()

    def has_references(self):
        if settings.CMIS_ENABLED:
            if (
                BesluitInformatieObject.objects.filter(
                    _informatieobject_url=self.get_url()
                ).exists()
                or ZaakInformatieObject.objects.filter(
                    _informatieobject_url=self.get_url()
                ).exists()
            ):
                return True
            else:
                return False
        else:
            if (
                self.canonical.besluitinformatieobject_set.exists()
                or self.canonical.zaakinformatieobject_set.exists()
            ):
                return True
            else:
                return False

    def get_url(self):
        eio_path = reverse(
            "enkelvoudiginformatieobject-detail",
            kwargs={"version": "1", "uuid": self.uuid},
        )
        return make_absolute_uri(eio_path)

    def has_gebruiksrechten(self):
        if settings.CMIS_ENABLED:
            eio_url = self.get_url()
            return Gebruiksrechten.objects.filter(informatieobject=eio_url).exists()
        else:
            return self.canonical.gebruiksrechten_set.exists()


class BestandsDeel(models.Model):
    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    informatieobject = models.ForeignKey(
        "EnkelvoudigInformatieObjectCanonical",
        on_delete=models.CASCADE,
        related_name="bestandsdelen",
        null=True,
        blank=True,
    )
    informatieobject_uuid = models.UUIDField(
        verbose_name=_("EnkelvoudigInformatieObject UUID"),
        help_text=_(
            "De unieke identifier van het gerelateerde EnkelvoudigInformatieObject in het "
            "achterliggende Document Management Systeem."
        ),
        blank=True,
        null=True,
    )
    volgnummer = models.PositiveIntegerField(
        help_text=_("Een volgnummer dat de volgorde van de bestandsdelen aangeeft.")
    )
    omvang = models.PositiveBigIntegerField(
        help_text=_("De grootte van dit specifieke bestandsdeel.")
    )
    inhoud = PrivateMediaFileField(
        upload_to="part-uploads/%Y/%m/",
        blank=True,
        help_text=_("De (binaire) bestandsinhoud van dit specifieke bestandsdeel."),
    )
    _voltooid = models.BooleanField(default=False)
    datetime_created = models.DateTimeField(_("datetime created"), auto_now_add=True)

    objects = BestandsDeelQuerySet.as_manager()

    class Meta:
        verbose_name = "bestandsdeel"
        verbose_name_plural = "bestandsdelen"
        constraints = [
            models.UniqueConstraint(
                fields=("informatieobject", "volgnummer"),
                condition=Q(informatieobject__isnull=False),
                name="unique_informatieobject_fk_and_volgnummer",
            ),
            models.UniqueConstraint(
                fields=("informatieobject_uuid", "volgnummer"),
                condition=Q(informatieobject_uuid__isnull=False),
                name="unique_informatieobject_uuid_and_volgnummer",
            ),
            models.CheckConstraint(
                check=Q(omvang__gt=0),
                name="check_omvang",
            ),
            models.CheckConstraint(
                check=Q(
                    informatieobject__isnull=True, informatieobject_uuid__isnull=False
                )
                | Q(informatieobject__isnull=False, informatieobject_uuid__isnull=True),
                name="informatieobject_fk_or_informatieobject_mutex",
            ),
        ]

    def unique_representation(self):
        informatieobject = self.informatieobject.latest_version
        return f"({informatieobject.unique_representation()}) - {self.volgnummer}"

    def get_informatieobject(self, permission_main_object=None):
        """
        For the CMIS case it retrieves the EnkelvoudigInformatieObject from Alfresco and returns it as a django type
        """
        if settings.CMIS_ENABLED:
            eio_uuid = self.informatieobject_uuid
            return (
                EnkelvoudigInformatieObject.objects.filter(uuid=eio_uuid)
                .order_by("-versie")
                .first()
            )
        else:
            return self.informatieobject.latest_version

    def get_current_lock_value(self) -> str:
        informatieobject = self.get_informatieobject()
        return informatieobject.canonical.lock

    def save(self, *args, **kwargs) -> None:
        if bool(self.inhoud.name):
            self._voltooid = self.inhoud.size == self.omvang
        return super().save(*args, **kwargs)

    @property
    def voltooid(self) -> bool:
        if self._voltooid is not None:
            return self._voltooid

        if not bool(self.inhoud.name):
            return False

        return self.inhoud.size == self.omvang


class Gebruiksrechten(APIMixin, CMISETagMixin, models.Model, CMISClientMixin):
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
        _("einddatum"),
        blank=True,
        null=True,
        help_text=_(
            "Einddatum van de periode waarin de gebruiksrechtvoorwaarden van toepassing zijn."
        ),
        db_index=True,
    )

    objects = GebruiksrechtenAdapterManager()

    class Meta:
        verbose_name = _("gebruiksrecht informatieobject")
        verbose_name_plural = _("gebruiksrechten informatieobject")

    def __str__(self):
        if settings.CMIS_ENABLED:
            return "(virtual gebruiksrechten instance)"
        return str(self.informatieobject.latest_version)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if settings.CMIS_ENABLED:
            model_data = model_to_dict(self)
            # If the gebruiksrechten doesn't exist, create it, otherwise update it
            try:
                # Check if the gebruiksrechten exists already in the CMIS backend
                self.cmis_client.get_content_object(
                    drc_uuid=self.uuid, object_type="gebruiksrechten"
                )
                # Update the instance in the storage backend
                Gebruiksrechten.objects.filter(uuid=self.uuid).update(**model_data)
            except exceptions.DocumentDoesNotExistError:
                Gebruiksrechten.objects.create(**model_data)

            return

        informatieobject_versie = self.informatieobject.latest_version
        # ensure the indication is set properly on the IO
        if not informatieobject_versie.indicatie_gebruiksrecht:
            informatieobject_versie.indicatie_gebruiksrecht = True
            informatieobject_versie.save()
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if not settings.CMIS_ENABLED:
            super().delete(*args, **kwargs)
            informatieobject = self.informatieobject
            other_gebruiksrechten = informatieobject.gebruiksrechten_set.exclude(
                pk=self.pk
            )
            if not other_gebruiksrechten.exists():
                informatieobject_versie = self.informatieobject.latest_version
                informatieobject_versie.indicatie_gebruiksrecht = None
                informatieobject_versie.save()
        else:
            # Check if there are other Gebruiksrechten for the EnkelvoudigInformatieObject in alfresco
            eio_url = self.get_informatieobject_url()
            if Gebruiksrechten.objects.filter(informatieobject=eio_url).count() <= 1:
                eio = self.get_informatieobject()
                eio.indicatie_gebruiksrecht = None
                eio.save()
            self.cmis_client.delete_content_object(
                self.uuid, object_type="gebruiksrechten"
            )

    def get_informatieobject_url(self):
        """
        Retrieves the EnkelvoudigInformatieObject url from Alfresco
        """
        cmis_gebruiksrechten = self.cmis_client.get_content_object(
            self.uuid, object_type="gebruiksrechten"
        )
        return cmis_gebruiksrechten.informatieobject

    def get_informatieobject(self, permission_main_object=None):
        """
        Retrieves the EnkelvoudigInformatieObject from Alfresco and returns it as a django type
        """
        if settings.CMIS_ENABLED:
            # Get the uuid of the object and retrieve it from alfresco
            cmis_gebruiksrechten = self.cmis_client.get_content_object(
                self.uuid, object_type="gebruiksrechten"
            )
            # From the URL of the informatie object, retrieve the EnkelvoudigInformatieObject
            eio_uuid = cmis_gebruiksrechten.informatieobject.split("/")[-1]
            return EnkelvoudigInformatieObject.objects.get(uuid=eio_uuid)
        elif permission_main_object:
            return getattr(self, permission_main_object).latest_version
        else:
            return self.informatieobject.latest_version

    def unique_representation(self):
        if settings.CMIS_ENABLED:
            try:
                informatieobject = self.get_informatieobject()
            # This happens when the audittrail accesses unique_representation() after deleting the gebruiksrechten
            except exceptions.DocumentDoesNotExistError:
                return f"{self.uuid}"
        else:
            informatieobject = self.informatieobject.latest_version
        return f"({informatieobject.unique_representation()}) - {self.omschrijving_voorwaarden[:50]}"


class ObjectInformatieObject(CMISETagMixin, models.Model, CMISClientMixin):
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
        choices=ObjectInformatieObjectTypes.choices,
        help_text="Het type van het gerelateerde OBJECT.",
    )

    # relations to the possible other objects
    _object_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern API.",
    )
    _object_relative_url = RelativeURLField(
        _("besluit relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern API.",
    )
    _object_url = ServiceUrlField(
        base_field="_object_base_url",
        relative_field="_object_relative_url",
        verbose_name=_("extern object"),
        blank=True,
        null=True,
        max_length=1000,
    )
    verzoek = AliasServiceUrlField(
        source_field=_object_url,
        allow_write_when=lambda instance: instance.object_type
        == ObjectInformatieObjectTypes.verzoek,
        blank=True,
    )

    _zaak = models.ForeignKey(
        "zaken.Zaak", on_delete=models.CASCADE, null=True, blank=True
    )
    zaak = FkOrServiceUrlField(
        fk_field="_zaak",
        url_field="_object_url",
        blank=True,
        null=True,
    )

    _besluit = models.ForeignKey(
        "besluiten.Besluit", on_delete=models.CASCADE, null=True, blank=True
    )
    besluit = FkOrServiceUrlField(
        fk_field="_besluit",
        url_field="_object_url",
        blank=True,
        null=True,
    )

    objects = ObjectInformatieObjectAdapterManager()

    class Meta:
        verbose_name = _("objectinformatieobject")
        verbose_name_plural = _("objectinformatieobjecten")
        # check that only one loose-fk field (fk or url) is filled
        constraints = [
            # mutual exclusive check on zaak fk, besluit fk or object url
            models.CheckConstraint(
                check=(
                    Q(
                        _object_base_url__isnull=True,
                        _zaak__isnull=False,
                        _besluit__isnull=True,
                    )
                    | Q(
                        _object_base_url__isnull=True,
                        _zaak__isnull=True,
                        _besluit__isnull=False,
                    )
                    | Q(
                        _object_base_url__isnull=False,
                        _zaak__isnull=True,
                        _besluit__isnull=True,
                    )
                ),
                name="object_reference_fields_mutex",
            ),
            # correct field filled, depending on object type
            models.CheckConstraint(
                check=(
                    Q(
                        Q(_zaak__isnull=False) | Q(_object_base_url__isnull=False),
                        object_type=ObjectInformatieObjectTypes.zaak,
                    )
                    | Q(
                        Q(_besluit__isnull=False) | Q(_object_base_url__isnull=False),
                        object_type=ObjectInformatieObjectTypes.besluit,
                    )
                    | Q(
                        Q(_object_base_url__isnull=False),
                        object_type=ObjectInformatieObjectTypes.verzoek,
                    )
                ),
                name="correct_field_set_for_object_type",
            ),
            # unique constraints - combination of document and object may only occur once
            models.UniqueConstraint(
                fields=("informatieobject", "_zaak"), name="unique_io_zaak_local"
            ),
            models.UniqueConstraint(
                fields=("informatieobject", "_besluit"), name="unique_io_besluit_local"
            ),
            models.UniqueConstraint(
                fields=("informatieobject", "_object_base_url", "_object_relative_url"),
                name="unique_io_object_external",
                condition=Q(_object_base_url__isnull=False),
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
        if settings.CMIS_ENABLED:
            informatieobject = self.get_informatieobject()
        else:
            informatieobject = self.informatieobject.latest_version
        if self.object_type == ObjectInformatieObjectTypes.verzoek:
            # string
            parsed = urlparse(self.object)
            io_id = parsed.path.rsplit("/", 1)[-1]
        else:
            io_id = self.object.identificatie
        return f"({informatieobject.unique_representation()}) - {io_id}"

    def save(self, *args, **kwargs):
        if not settings.CMIS_ENABLED:
            super().save(*args, **kwargs)

    def get_url(self):
        oio_path = reverse(
            "objectinformatieobject-detail",
            kwargs={"version": "1", "uuid": self.uuid},
        )
        return make_absolute_uri(oio_path)

    def delete(self, *args, **kwargs):
        if not settings.CMIS_ENABLED:
            super().delete(*args, **kwargs)
        else:
            self.cmis_client.delete_content_object(self.uuid, object_type="oio")

    def get_informatieobject(self, permission_main_object=None):
        """
        For the CMIS case it retrieves the EnkelvoudigInformatieObject from Alfresco and returns it as a django type
        """
        if settings.CMIS_ENABLED:
            eio_url = self.get_informatieobject_url()
            # From the URL of the informatie object, retrieve the EnkelvoudigInformatieObject
            eio_uuid = eio_url.split("/")[-1]
            return EnkelvoudigInformatieObject.objects.get(uuid=eio_uuid)
        elif permission_main_object:
            return getattr(self, permission_main_object).latest_version
        else:
            return self.informatieobject.latest_version

    def get_informatieobject_url(self):
        """
        Retrieves the EnkelvoudigInformatieObject url from Alfresco
        """
        cmis_oio = self.cmis_client.get_content_object(self.uuid, object_type="oio")
        return cmis_oio.informatieobject

    def does_besluitinformatieobject_exist(self):
        """
        Checks if the corresponding BesluitInformatieObject still exists
        """
        if settings.CMIS_ENABLED:
            eio_url = self.get_informatieobject_url()
            return BesluitInformatieObject.objects.filter(
                informatieobject=eio_url, besluit=self.besluit
            ).exists()
        else:
            return BesluitInformatieObject.objects.filter(
                informatieobject=self.informatieobject, besluit=self.besluit
            ).exists()

    def does_zaakinformatieobject_exist(self):
        """
        Checks if the corresponding ZaakInformatieObject still exists
        """
        if settings.CMIS_ENABLED:
            eio_url = self.get_informatieobject_url()
            return ZaakInformatieObject.objects.filter(
                informatieobject=eio_url, zaak=self.zaak
            ).exists()
        else:
            return ZaakInformatieObject.objects.filter(
                informatieobject=self.informatieobject, zaak=self.zaak
            ).exists()


# gebaseerd op https://www.gemmaonline.nl/index.php/Rgbz_2.0/doc/relatieklasse/verzending
class Verzending(APIMixin, CMISETagMixin, models.Model):
    uuid = models.UUIDField(
        unique=True,
        default=_uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)",
    )
    betrokkene = models.URLField(
        _("betrokkene"),
        help_text=_(
            "URL-referentie naar de betrokkene waarvan het informatieobject is"
            " ontvangen of waaraan dit is verzonden."
        ),
    )
    informatieobject = models.ForeignKey(
        "EnkelvoudigInformatieObjectCanonical",
        verbose_name=_("informatieobject"),
        help_text=_(
            "URL-referentie naar het informatieobject dat is ontvangen of verzonden."
        ),
        on_delete=models.CASCADE,
        related_name="verzendingen",
    )
    aard_relatie = models.CharField(
        _("aard relatie"),
        max_length=255,
        choices=AfzenderTypes.choices,
        help_text=_(
            "Omschrijving van de aard van de relatie van de BETROKKENE tot het"
            " INFORMATIEOBJECT."
        ),
    )

    telefoonnummer = models.CharField(
        _("telefoonnummer"),
        max_length=15,
        help_text=_("telefoonnummer van de ontvanger of afzender."),
        blank=True,
    )
    faxnummer = models.CharField(
        _("faxnummer"),
        max_length=15,
        help_text=_("faxnummer van de ontvanger of afzender."),
        blank=True,
    )
    emailadres = models.EmailField(
        _("emailadres"),
        max_length=100,
        help_text=_("emailadres van de ontvanger of afzender."),
        blank=True,
    )
    mijn_overheid = models.BooleanField(
        _("mijn overheid"),
        default=False,
        help_text=_(
            "is het informatieobject verzonden via mijnOverheid naar de ontvanger."
        ),
    )
    toelichting = models.CharField(
        _("toelichting"),
        max_length=200,
        help_text=_("Verduidelijking van de afzender- of geadresseerde-relatie."),
        blank=True,
    )

    ontvangstdatum = models.DateField(
        _("ontvangstdatum"),
        help_text=_(
            "De datum waarop het INFORMATIEOBJECT ontvangen is. Verplicht te"
            " registreren voor INFORMATIEOBJECTen die van buiten de zaakbehandelende"
            " organisatie(s) ontvangen zijn. Ontvangst en verzending is voorbehouden"
            " aan documenten die van of naar andere personen ontvangen of verzonden"
            " zijn waarbij die personen niet deel uit maken van de behandeling van"
            " de zaak waarin het document een rol speelt. Vervangt het gelijknamige"
            " attribuut uit Informatieobject. Verplicht gevuld wanneer aardRelatie"
            " de waarde 'afzender' heeft."
        ),
        blank=True,
        null=True,
    )

    verzenddatum = models.DateField(
        _("verzenddatum"),
        help_text=_(
            "De datum waarop het INFORMATIEOBJECT verzonden is, zoals deze"
            " op het INFORMATIEOBJECT vermeld is. Dit geldt voor zowel inkomende"
            " als uitgaande INFORMATIEOBJECTen. Eenzelfde informatieobject kan"
            " niet tegelijk inkomend en uitgaand zijn. Ontvangst en verzending"
            " is voorbehouden aan documenten die van of naar andere personen"
            " ontvangen of verzonden zijn waarbij die personen niet deel uit"
            " maken van de behandeling van de zaak waarin het document een rol"
            " speelt. Vervangt het gelijknamige attribuut uit Informatieobject."
            " Verplicht gevuld wanneer aardRelatie de waarde 'geadresseerde' heeft."
        ),
        blank=True,
        null=True,
    )

    contact_persoon = models.URLField(
        _("contactpersoon"),
        help_text=_(
            "URL-referentie naar de persoon die als aanspreekpunt fungeert voor"
            " de BETROKKENE inzake het ontvangen of verzonden INFORMATIEOBJECT."
        ),
        max_length=1000,
    )
    contactpersoonnaam = models.CharField(
        _("contactpersoonnaam"),
        help_text=_(
            "De opgemaakte naam van de persoon die als aanspreekpunt fungeert voor"
            "de BETROKKENE inzake het ontvangen of verzonden INFORMATIEOBJECT."
        ),
        max_length=40,
        blank=True,
    )

    binnenlands_correspondentieadres_huisletter = models.CharField(
        _("huisletter"),
        help_text=(
            "Een door of namens het bevoegd gemeentelijk orgaan ten aanzien van een"
            " adresseerbaar object toegekende toevoeging aan een huisnummer in de"
            " vorm van een alfanumeriek teken."
        ),
        max_length=1,
        blank=True,
    )
    binnenlands_correspondentieadres_huisnummer = models.PositiveIntegerField(
        _("huisnummer"),
        help_text=(
            "Een door of namens het bevoegd gemeentelijk orgaan ten aanzien van"
            " een adresseerbaar object toegekende nummering."
        ),
        validators=[MinValueValidator(1), MaxValueValidator(99999)],
        blank=True,
        null=True,
    )
    binnenlands_correspondentieadres_huisnummer_toevoeging = models.CharField(
        _("huisnummer toevoeging"),
        help_text=(
            "Een door of namens het bevoegd gemeentelijk orgaan ten aanzien van"
            " een adresseerbaar object toegekende nadere toevoeging aan een huisnummer"
            " of een combinatie van huisnummer en huisletter."
        ),
        max_length=4,
        blank=True,
    )
    binnenlands_correspondentieadres_naam_openbare_ruimte = models.CharField(
        _("naam openbare ruimte"),
        help_text=(
            "Een door het bevoegde gemeentelijke orgaan aan een GEMEENTELIJKE "
            " OPENBARE RUIMTE toegekende benaming."
        ),
        max_length=80,
        blank=True,
    )
    binnenlands_correspondentieadres_postcode = NLPostcodeField(
        _("postcode"),
        help_text=_(
            "De door TNT Post vastgestelde code behorende bij een bepaalde combinatie"
            " van een naam van een woonplaats, naam van een openbare ruimte en een huisnummer."
        ),
        blank=True,
    )
    binnenlands_correspondentieadres_woonplaatsnaam = models.CharField(
        _("woonplaatsnaam"),
        help_text=(
            "De door het bevoegde gemeentelijke orgaan aan een WOONPLAATS toegekende"
            " benaming."
        ),
        max_length=80,
        blank=True,
    )
    binnenlands_correspondentieadres = GegevensGroepType(
        {
            "huisletter": binnenlands_correspondentieadres_huisletter,
            "huisnummer": binnenlands_correspondentieadres_huisnummer,
            "huisnummer_toevoeging": binnenlands_correspondentieadres_huisnummer_toevoeging,
            "naam_openbare_ruimte": binnenlands_correspondentieadres_naam_openbare_ruimte,
            "postcode": binnenlands_correspondentieadres_postcode,
            "woonplaatsnaam": binnenlands_correspondentieadres_woonplaatsnaam,
        },
        required=False,
        optional=(
            "huisletter",
            "huisnummer_toevoeging",
            "postcode",
        ),
    )

    buitenlands_correspondentieadres_adres_buitenland_1 = models.CharField(
        _("adres buitenland 1"),
        max_length=35,
        help_text=_(
            "Het eerste deel dat behoort bij het afwijkend buitenlandse correspondentieadres"
            " van de betrokkene in zijn/haar rol bij de zaak."
        ),
        blank=True,
    )
    buitenlands_correspondentieadres_adres_buitenland_2 = models.CharField(
        _("adres buitenland 2"),
        max_length=35,
        help_text=_(
            "Het tweede deel dat behoort bij het afwijkend buitenlandse correspondentieadres"
            " van de betrokkene in zijn/haar rol bij de zaak."
        ),
        blank=True,
    )
    buitenlands_correspondentieadres_adres_buitenland_3 = models.CharField(
        _("adres buitenland 3"),
        max_length=35,
        help_text=_(
            "Het derde deel dat behoort bij het afwijkend buitenlandse correspondentieadres"
            " van de betrokkene in zijn/haar rol bij de zaak."
        ),
        blank=True,
    )
    buitenlands_correspondentieadres_land_postadres = models.URLField(
        _("land postadres"),
        help_text=_(
            "Het LAND dat behoort bij het afwijkend buitenlandse correspondentieadres"
            " van de betrokkene in zijn/haar rol bij de zaak."
        ),
        blank=True,
    )
    buitenlands_correspondentieadres = GegevensGroepType(
        {
            "adres_buitenland_1": buitenlands_correspondentieadres_adres_buitenland_1,
            "adres_buitenland_2": buitenlands_correspondentieadres_adres_buitenland_2,
            "adres_buitenland_3": buitenlands_correspondentieadres_adres_buitenland_3,
            "land_postadres": buitenlands_correspondentieadres_land_postadres,
        },
        required=False,
        optional=(
            "adres_buitenland_2",
            "adres_buitenland_3",
        ),
    )

    correspondentie_postadres_postbus_of_antwoord_nummer = models.PositiveIntegerField(
        _("postbus-of antwoordnummer"),
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
        help_text=_(
            "De numerieke aanduiding zoals deze door de Nederlandse PTT is vastgesteld"
            " voor postbusadressen en antwoordnummeradressen."
        ),
        blank=True,
        null=True,
    )
    correspondentie_postadres_postcode = NLPostcodeField(
        _("postadres postcode"),
        help_text=_(
            "De officiële Nederlandse PTT codering, bestaande uit een numerieke"
            " woonplaatscode en een alfabetische lettercode."
        ),
        blank=True,
    )
    correspondentie_postadres_postadrestype = models.CharField(
        _("postadrestype"),
        max_length=255,
        choices=PostAdresTypes.choices,
        help_text=_("Aanduiding van het soort postadres."),
        blank=True,
    )
    correspondentie_postadres_woonplaatsnaam = models.CharField(
        _("woonplaatsnaam"),
        max_length=80,
        help_text=_(
            "De door het bevoegde gemeentelijke orgaan aan een WOONPLAATS toegekende"
            " benaming."
        ),
        blank=True,
    )
    correspondentie_postadres = GegevensGroepType(
        {
            "post_bus_of_antwoordnummer": correspondentie_postadres_postbus_of_antwoord_nummer,
            "postadres_postcode": correspondentie_postadres_postcode,
            "postadres_type": correspondentie_postadres_postadrestype,
            "woonplaatsnaam": correspondentie_postadres_woonplaatsnaam,
        },
        required=False,
    )

    objects = InformatieobjectRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = _("Verzending")
        verbose_name_plural = _("Verzendingen")

    def __str__(self):
        return _("Verzending %(uuid)s") % {"uuid": str(self.uuid)}

    @transaction.atomic
    def save(self, *args, **kwargs):
        if settings.CMIS_ENABLED:
            raise NotImplementedError("CMIS is not supported for Verzending")

        super().save(*args, **kwargs)

    def get_informatieobject(self, permission_main_object=None):
        if settings.CMIS_ENABLED:
            raise NotImplementedError("CMIS is not supported for Verzending")
        elif permission_main_object:
            return getattr(self, permission_main_object).latest_version
        else:
            return self.informatieobject.latest_version
