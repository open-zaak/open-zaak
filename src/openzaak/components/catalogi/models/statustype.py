import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max
from django.utils.translation import ugettext_lazy as _


class CheckListItem(models.Model):
    """
    Te controleren aandachtspunt voorafgaand aan het bereiken van een status van het STATUSTYPE.

    Door één of meer checklistitems op te nemen bij een status, wordt een checklist verkregen met
    punten waaraan aandacht besteed moet worden teneinde die status te bereiken.

    # TODO: wanneer sub attributeen op een StatusType worden gegeven, dient er dan een nieuwe instance van
    checklistItem te worden gemaakt?
    """
    itemnaam = models.CharField(_('itemnaam'), max_length=30, help_text=_(
        'De betekenisvolle benaming van het checklistitem'))
    vraagstelling = models.CharField(_('vraagstelling'), max_length=255, help_text=_(
        'Een betekenisvolle vraag waaruit blijkt waarop het aandachtspunt gecontroleerd moet worden.'))
    # verplicht is gedefinieerd als BooleanField, en informeren als AN1, beide met waardeverzameling J/N
    verplicht = models.BooleanField(
        _('verplicht'), default=False,
        help_text=_('Het al dan niet verplicht zijn van controle van het '
                    'aandachtspunt voorafgaand aan het bereiken van de status '
                    'van het gerelateerde STATUSTYPE.'))
    toelichting = models.CharField(_('toelichting'), max_length=1000, blank=True, null=True, help_text=_(
        'Beschrijving van de overwegingen bij het controleren van het aandachtspunt'))


class StatusType(models.Model):
    """
    Generieke aanduiding van de aard van een STATUS

    Toelichting objecttype
    Zaken van eenzelfde zaaktype doorlopen alle dezelfde statussen, tenzij de zaak voortijdig
    beeëindigd wordt. Met STATUSTYPE worden deze statussen benoemd bij het desbetreffende
    zaaktype. De attribuutsoort ‘Doorlooptijd status’ is niet bedoeld om daarmee voor een
    individuele zaak de statussen te plannen maar om geïnteresseerden informatie te verschaffen
    over de termijn waarop normaliter een volgende status bereikt wordt.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )

    # relations
    zaaktype = models.ForeignKey(
        'ZaakType', verbose_name=_('is van'), related_name='statustypen', on_delete=models.CASCADE,
        help_text=_('URL-referentie naar het ZAAKTYPE van ZAAKen waarin STATUSsen van dit STATUSTYPE bereikt kunnen worden.')
    )

    # attributes
    statustype_omschrijving = models.CharField(
        _('omschrijving'), max_length=80,
        help_text=_('Een korte, voor de initiator van de zaak relevante, omschrijving van de '
                    'aard van de STATUS van zaken van een ZAAKTYPE.')
    )
    statustype_omschrijving_generiek = models.CharField(
        _('omschrijving generiek'), max_length=80, blank=True,
        help_text=_('Algemeen gehanteerde omschrijving van de aard van STATUSsen van het STATUSTYPE'))
    # waardenverzameling is 0001 - 9999, omdat int('0001') == 1 als PositiveSmallIntegerField
    statustypevolgnummer = models.PositiveSmallIntegerField(
        _('statustypevolgnummer'), validators=[MinValueValidator(1), MaxValueValidator(9999)], help_text=_(
            'Een volgnummer voor statussen van het STATUSTYPE binnen een zaak.'))
    doorlooptijd_status = models.PositiveSmallIntegerField(
        _('doorlooptijd status'), blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(999)],
        help_text=_('De door de zaakbehandelende organisatie(s) gestelde norm voor de doorlooptijd voor het bereiken '
                    'van statussen van dit STATUSTYPE bij het desbetreffende ZAAKTYPE, vanaf het bereiken van '
                    'de voorafgaande status')
    )
    checklistitem = models.ManyToManyField(
        'catalogi.CheckListItem', verbose_name=_('checklistitem'), blank=True, help_text=_(
            'Te controleren aandachtspunt voorafgaand aan het bereiken van een status van het STATUSTYPE.'))
    informeren = models.BooleanField(
        _('informeren'), default=False,
        help_text=_('Aanduiding die aangeeft of na het zetten van een STATUS van dit STATUSTYPE de Initiator moet '
                    'worden geïnformeerd over de statusovergang.')
    )
    statustekst = models.CharField(
        _('statustekst'), max_length=1000, blank=True,
        help_text=_('De tekst die wordt gebruikt om de Initiator te informeren over het bereiken van een STATUS van '
                    'dit STATUSTYPE bij het desbetreffende ZAAKTYPE.')
    )
    toelichting = models.CharField(_('toelichting'), max_length=1000, blank=True, null=True, help_text=_(
        'Een eventuele toelichting op dit STATUSTYPE.'))

    # TODO: deze relatie is gedefinieerd op RolType en heeft de volgende regel:
    #  De relatiesoort ontstaat en eindigt alleen (materiële historie) op een datum die gelijk is resp. een dag
    # ligt voor een Versiedatum van het gerelateerd zaaktype.er is een regel voor deze relatie
    roltypen = models.ManyToManyField(
        'catalogi.RolType', verbose_name=_('roltypen'), related_name='mag_zetten',
        help_text=_('De STATUSTYPEn die een betrokkene in een rol van dit ROLTYPE mag zetten.'))

    class Meta:
        unique_together = ('zaaktype', 'statustypevolgnummer')
        verbose_name = _('Statustype')
        verbose_name_plural = _('Statustypen')
        ordering = unique_together

        filter_fields = (
            'zaaktype',
            'informeren',
        )
        ordering_fields = filter_fields
        search_fields = (
            'statustype_omschrijving',
            'statustype_omschrijving_generiek',
            'statustypevolgnummer',
        )

    def is_eindstatus(self):
        """
        Een `StatusType` betreft een eindstatus als het volgnummer van het
        `StatusType` de hoogste is binnen het `ZaakType`.

        # TODO: Can be cached on the model.
        """
        max_statustypevolgnummer = self.zaaktype.statustypen.aggregate(
            result=Max('statustypevolgnummer'))['result']

        return max_statustypevolgnummer == self.statustypevolgnummer

    def __str__(self):
        return '{} - {}'.format(self.zaaktype, self.statustypevolgnummer)
