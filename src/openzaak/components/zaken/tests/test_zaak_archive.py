# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/345
"""
from datetime import date

from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    Archiefstatus,
    BrondatumArchiefprocedureAfleidingswijze,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import get_validation_errors, reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.constants import Statussen
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import JWTAuthMixin, get_eio_response, mock_client

from .factories import (
    RelevanteZaakRelatieFactory,
    WozWaardeFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, get_operation_url, get_zaak_response, isodatetime

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


class US345TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_create_zaak_causes_archiving_defaults(self):
        """
        Create ZAAK and validate default archive attributes
        """
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        zaak_create_url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "startdatum": "2018-07-25",
            "einddatum": "2018-08-25",
            "einddatumGepland": "2018-08-25",
            "toelichting": "",
            "omschrijving": "",
        }

        response = self.client.post(zaak_create_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()

        self.assertIsNone(data["archiefnominatie"])
        self.assertEqual(data["archiefstatus"], Archiefstatus.nog_te_archiveren)
        self.assertIsNone(data["archiefactiedatum"])

    def test_can_set_archiefnominatie(self):
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)

        data = {"archiefnominatie": Archiefnominatie.vernietigen}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefactiedatum(self):
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)

        data = {"archiefactiedatum": date(2019, 1, 1)}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_without_archiefnominatie_and_archiefactiedatum(
        self,
    ):
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)

        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_can_set_archiefstatus_with_archiefnominatie_and_archiefactiedatum(self):
        zaak = ZaakFactory.create()
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)

        data = {
            "archiefnominatie": Archiefnominatie.vernietigen,
            "archiefactiedatum": date(2019, 1, 1),
            "archiefstatus": Archiefstatus.gearchiveerd,
        }

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefstatus_when_archiefnominatie_and_archiefactiedatum_already_set(
        self,
    ):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)

        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_can_set_archiefstatus_when_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status="gearchiveerd")
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io.canonical)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_when_not_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status="in_bewerking")
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io.canonical)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_add_resultaat_on_zaak_causes_archiefnominatie_to_be_copied(self):
        """
        Add RESULTAAT that causes `archiefnominatie` to be copied from RESULTAATTYPE.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)

        # add a result for the case
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }
        self.assertIsNone(zaak.archiefnominatie)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url("status_create")
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefnominatie, Archiefnominatie.blijvend_bewaren)

    def test_add_resultaat_on_zaak_without_einddatum(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to remain `None`.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        self.assertIsNone(zaak.archiefactiedatum)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url("status_create")
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    def test_add_resultaat_on_zaak_with_einddatum_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        self.assertIsNone(zaak.archiefactiedatum)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url("status_create")

        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2028, 10, 18))

    def test_add_resultaat_on_zaak_with_eigenschap_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        ZaakEigenschapFactory.create(
            zaak=zaak, _naam="brondatum", waarde=isodatetime(2019, 1, 1)
        )
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.eigenschap,
            brondatum_archiefprocedure_datumkenmerk="brondatum",
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        self.assertIsNone(zaak.archiefactiedatum)

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url("status_create")
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    def test_add_resultaat_on_zaak_with_incorrect_eigenschap_fails(self):
        """
        Attempt to add RESULTAAT with incorrect ZTC-configuration.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.eigenschap,
            brondatum_archiefprocedure_datumkenmerk="brondatum",
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        # add resultaat
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url("status_create")
        data = {
            "zaak": zaak_url,
            "statustype": statustype_url,
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_resultaat_on_zaak_with_hoofdzaak_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        hoofd_zaak = ZaakFactory.create(einddatum=date(2019, 1, 1))

        zaak = ZaakFactory.create(hoofdzaak=hoofd_zaak)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        # add resultaat
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        status_create_url = get_operation_url("status_create")
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2029, 1, 1))

    def test_add_resultaat_on_zaak_with_ander_datumkenmerk_causes_archiefactiedatum_to_remain_empty(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to remain empty. It needs to be manually set based on the
        information in the RESULTAATTYPE.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk,
            brondatum_archiefprocedure_datumkenmerk="einddatum",
            brondatum_archiefprocedure_registratie="LichtgevendeObjectenRegistratie",
            brondatum_archiefprocedure_objecttype="Lantaarnpaal",
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        # add resultaat
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.archiefactiedatum)

    def test_add_resultaat_on_zaak_with_remote_zaakobjecten_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaak_object1 = ZaakObjectFactory.create(zaak=zaak)
        zaak_object2 = ZaakObjectFactory.create(
            zaak=zaak, object_type=zaak_object1.object_type
        )
        for object in [zaak_object1.object, zaak_object2.object]:
            Service.objects.create(
                api_type=APITypes.orc,
                api_root=object,
                label="BAG",
                auth_type=AuthTypes.no_auth,
            )
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.zaakobject,
            brondatum_archiefprocedure_datumkenmerk="einddatum",
            brondatum_archiefprocedure_objecttype=zaak_object1.object_type,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        responses = {
            zaak_object1.object: {"einddatum": isodatetime(2019, 1, 1)},
            zaak_object2.object: {"einddatum": isodatetime(2022, 1, 1)},
        }

        # add resultaat
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        with mock_client(responses):
            response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2032, 1, 1))

    def test_add_resultaat_on_zaak_with_local_zaakobjecten_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaak_object1 = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type="woz_waarde"
        )
        zaak_object2 = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type="woz_waarde"
        )
        WozWaardeFactory.create(zaakobject=zaak_object1, waardepeildatum="2010-1-1")
        WozWaardeFactory.create(zaakobject=zaak_object2, waardepeildatum="2013-1-1")
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.zaakobject,
            brondatum_archiefprocedure_datumkenmerk="waardepeildatum",
            brondatum_archiefprocedure_objecttype=zaak_object1.object_type,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)

        # add resultaat
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2023, 1, 1))

    def test_add_resultaat_on_zaak_with_procestermijn_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.termijn,
            brondatum_archiefprocedure_procestermijn="P5Y",
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2028, 10, 18))

    def test_add_resultaat_on_zaak_with_afleidingswijze_ingangsdatum_besluit_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        BesluitFactory.create(zaak=zaak, ingangsdatum="2020-01-01")
        BesluitFactory.create(zaak=zaak, ingangsdatum="2018-01-01")

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2025, 1, 1))

    def test_add_resultaat_on_zaak_with_afleidingswijze_ingangsdatum_besluit_without_besluiten_gives_400(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "archiefactiedatum-error")

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, None)

    def test_add_resultaat_on_zaak_with_afleidingswijze_vervaldatum_besluit_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        BesluitFactory.create(zaak=zaak, vervaldatum="2021-01-01")
        BesluitFactory.create(zaak=zaak, vervaldatum="2020-01-01")

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2026, 1, 1))

    def test_add_resultaat_on_zaak_with_afleidingswijze_vervaldatum_besluit_and_besluit_vervaldatum_none_gives_400(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        BesluitFactory.create(zaak=zaak, vervaldatum=None)

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "archiefactiedatum-error")

    def test_add_resultaat_on_zaak_with_afleidingswijze_vervaldatum_besluit_without_besluiten_gives_400(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "archiefactiedatum-error")

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, None)

    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_add_resultaat_on_zaak_with_afleidingswijze_gerelateerde_zaak_causes_archiefactiedatum_to_be_set(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak2 = ZaakFactory.create(einddatum="2022-01-01")
        zaak3 = ZaakFactory.create(einddatum="2025-01-01")
        RelevanteZaakRelatieFactory.create(zaak=zaak, url=zaak2)
        RelevanteZaakRelatieFactory.create(zaak=zaak, url=zaak3)

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": f"http://testserver.com{zaak_url}",
            "resultaattype": f"http://testserver.com{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(
            resultaat_create_url, data, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": f"http://testserver.com{zaak_url}",
            "statustype": f"http://testserver.com{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data, HTTP_HOST="testserver.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, date(2030, 1, 1))

    def test_add_resultaat_on_zaak_with_afleidingswijze_gerelateerde_zaak_without_relevante_zaken_gives_400(
        self,
    ):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        response = self.client.post(status_create_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "archiefactiedatum-error")

        zaak.refresh_from_db()
        self.assertEqual(zaak.archiefactiedatum, None)


@tag("external-urls")
class ExternalDocumentsAPITests(JWTAuthMixin, APITestCase):
    """
    Test archiving with remote documents involved.
    """

    heeft_alle_autorisaties = True

    @requests_mock.Mocker()
    def test_cannot_set_archiefstatus_when_not_all_documents_are_gearchiveerd(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"

        m.get(
            REMOTE_DOCUMENT,
            json=get_eio_response(REMOTE_DOCUMENT, status=Statussen.ter_vaststelling),
        )

        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_add_resultaat_on_zaak_with_external_gerelateerde_zaak_(self):
        """
        Add RESULTAAT that causes `archiefactiedatum` to be set.
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaaktype_url = f"http://testserver.com{reverse(zaak.zaaktype)}"

        zaak2 = "https://external.nl/zaken/123"
        zaak2_data = get_zaak_response(zaak2, zaaktype_url)
        zaak2_data["einddatum"] = "2022-01-01"
        zaak3 = "https://external.nl/zaken/456"
        zaak3_data = get_zaak_response(zaak3, zaaktype_url)
        zaak3_data["einddatum"] = "2025-01-01"
        RelevanteZaakRelatieFactory.create(zaak=zaak, url=zaak2)
        RelevanteZaakRelatieFactory.create(zaak=zaak, url=zaak3)

        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P5Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak,
            brondatum_archiefprocedure_procestermijn=None,
            zaaktype=zaak.zaaktype,
        )
        resultaattype_url = reverse(resultaattype)
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": f"http://testserver.com{zaak_url}",
            "resultaattype": f"http://testserver.com{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(
            resultaat_create_url, data, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # add final status to the case to close it and to calculate archive parameters
        status_create_url = get_operation_url("status_create")
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": f"http://testserver.com{zaak_url}",
            "statustype": f"http://testserver.com{statustype_url}",
            "datumStatusGezet": "2018-10-18T20:00:00Z",
        }

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri("GET", zaak2, json=zaak2_data)
            m.register_uri("GET", zaak3, json=zaak3_data)
            response = self.client.post(
                status_create_url, data, HTTP_HOST="testserver.com"
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        #
        # zaak.refresh_from_db()
        # self.assertEqual(zaak.archiefactiedatum, date(2030, 1, 1))
