# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from pathlib import Path

from django.test import TestCase, override_settings

from django_setup_configuration.exceptions import ConfigurationRunFailed
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.components.autorisaties.tests.factories import (
    ApplicatieFactory,
    AutorisatieFactory,
    CatalogusAutorisatieFactory,
)
from openzaak.components.catalogi.tests.factories import CatalogusFactory
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_ALLES_LEZEN
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_CREATE,
)
from openzaak.config.bootstrap.authorizations import (
    DISALLOWED_SETTINGS,
    AuthorizationConfigurationStep,
)

ZAAKTYPE1 = "https://acc.openzaak.nl/zaaktypen/1"
ZAAKTYPE2 = "https://external.acc.openzaak.nl/zaaktypen/2"
ZAAKTYPE3 = "https://acc.openzaak.nl/zaaktypen/3"
ZAAKTYPE4 = "https://acc.openzaak.nl/zaaktypen/4"


AUTH_FIXTURE_PATH = Path(__file__).parent / "files/auth.yaml"
INVALID_AUTH_FIXTURE_PATH = Path(__file__).parent / "files/auth_invalid.yaml"
DOMAIN_MAPPING_PATH = Path(__file__).parent / "files/domain_mapping.yaml"


@override_settings(AUTHORIZATIONS_CONFIG_FIXTURE_PATH=AUTH_FIXTURE_PATH)
class AuthorizationConfigurationTests(TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.catalogus = CatalogusFactory.create(
            uuid="6de0b166-8e76-477c-901d-123244e4d020"
        )

    def test_configure(self):
        AuthorizationConfigurationStep().configure()

        self.assertEqual(JWTSecret.objects.count(), 2)
        self.assertEqual(Applicatie.objects.count(), 2)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 1)

        jwt_secret_oz = JWTSecret.objects.get(identifier="open-zaak")
        self.assertEqual(jwt_secret_oz.secret, "oz-secret")

        jwt_secret_on = JWTSecret.objects.get(identifier="open-notificaties")
        self.assertEqual(jwt_secret_on.secret, "on-secret")

        applicatie_oz = Applicatie.objects.get(client_ids=["open-zaak"])

        autorisatie_oz = applicatie_oz.autorisaties.get()
        self.assertEqual(autorisatie_oz.component, ComponentTypes.zrc)
        self.assertEqual(
            autorisatie_oz.scopes,
            [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)],
        )
        self.assertEqual(autorisatie_oz.zaaktype, ZAAKTYPE1)
        self.assertEqual(
            autorisatie_oz.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.geheim,
        )

        catalogus_autorisatie_oz = applicatie_oz.catalogusautorisatie_set.get()
        self.assertEqual(catalogus_autorisatie_oz.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie_oz.component, ComponentTypes.drc)
        self.assertEqual(
            catalogus_autorisatie_oz.scopes, [str(SCOPE_DOCUMENTEN_ALLES_LEZEN)]
        )
        self.assertEqual(
            catalogus_autorisatie_oz.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        applicatie_on = Applicatie.objects.get(client_ids=["open-notificaties"])

        autorisatie_on = applicatie_on.autorisaties.get()
        self.assertEqual(autorisatie_on.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie_on.scopes, [str(SCOPE_ZAKEN_ALLES_LEZEN)])
        self.assertEqual(autorisatie_on.zaaktype, ZAAKTYPE2)
        self.assertEqual(
            autorisatie_on.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

    @override_settings(AUTHORIZATIONS_CONFIG_FIXTURE_PATH=INVALID_AUTH_FIXTURE_PATH)
    def test_configure_validate_fixture_fails(self):
        with self.assertRaises(ConfigurationRunFailed) as cm:
            AuthorizationConfigurationStep().configure()

        expected_error_msg = (
            "The following errors occurred while validating the authorization "
            "configuration fixture: \n"
            "* One or more authorizations are missing scopes."
        )

        self.assertEqual(str(cm.exception), expected_error_msg)
        self.assertEqual(JWTSecret.objects.count(), 0)
        self.assertEqual(Applicatie.objects.count(), 0)
        self.assertEqual(Autorisatie.objects.count(), 0)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 0)

    @override_settings(
        AUTHORIZATIONS_CONFIG_DOMAIN_MAPPING_PATH=DOMAIN_MAPPING_PATH,
        ENVIRONMENT="production",
    )
    def test_configure_domain_mapping(self):
        AuthorizationConfigurationStep().configure()

        self.assertEqual(JWTSecret.objects.count(), 2)
        self.assertEqual(Applicatie.objects.count(), 2)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 1)

        jwt_secret_oz = JWTSecret.objects.get(identifier="open-zaak")
        self.assertEqual(jwt_secret_oz.secret, "oz-secret")

        jwt_secret_on = JWTSecret.objects.get(identifier="open-notificaties")
        self.assertEqual(jwt_secret_on.secret, "on-secret")

        applicatie_oz = Applicatie.objects.get(client_ids=["open-zaak"])

        autorisatie_oz = applicatie_oz.autorisaties.get()
        self.assertEqual(autorisatie_oz.component, ComponentTypes.zrc)
        self.assertEqual(
            autorisatie_oz.scopes,
            [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)],
        )
        self.assertEqual(autorisatie_oz.zaaktype, "https://openzaak.nl/zaaktypen/1")
        self.assertEqual(
            autorisatie_oz.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.geheim,
        )

        catalogus_autorisatie_oz = applicatie_oz.catalogusautorisatie_set.get()
        self.assertEqual(catalogus_autorisatie_oz.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie_oz.component, ComponentTypes.drc)
        self.assertEqual(
            catalogus_autorisatie_oz.scopes, [str(SCOPE_DOCUMENTEN_ALLES_LEZEN)]
        )
        self.assertEqual(
            catalogus_autorisatie_oz.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        applicatie_on = Applicatie.objects.get(client_ids=["open-notificaties"])

        autorisatie_on = applicatie_on.autorisaties.get()
        self.assertEqual(autorisatie_on.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie_on.scopes, [str(SCOPE_ZAKEN_ALLES_LEZEN)])
        self.assertEqual(
            autorisatie_on.zaaktype, "https://external.openzaak.nl/zaaktypen/2"
        )
        self.assertEqual(
            autorisatie_on.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_configure_catalogus_does_not_exist(self):
        """
        Running `.configure` while some of the expected data (Catalogus) does not exist
        should raise errors
        """
        self.catalogus.delete()

        # Attempt to run the import
        with self.assertRaises(ConfigurationRunFailed):
            AuthorizationConfigurationStep().configure()

        self.assertEqual(JWTSecret.objects.count(), 0)
        self.assertEqual(Applicatie.objects.count(), 0)
        self.assertEqual(Autorisatie.objects.count(), 0)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 0)

    def test_configure_overwrite(self):
        """
        Running `.configure` twice should overwrite any changes made to the configurated
        Applicaties, Autorisaties, CatalogusAutorisaties and JWTSecrets
        """
        AuthorizationConfigurationStep().configure()

        secret_oz, secret_on = JWTSecret.objects.all()

        secret_oz.secret = "modified-secret"
        secret_oz.save()
        secret_on.secret = "modified-secret"
        secret_on.save()

        applicatie_oz, applicatie_on = Applicatie.objects.all()
        applicatie_oz.label = "Open Zaak"
        applicatie_oz.save()
        applicatie_oz.label = "Open Notificaties"
        applicatie_oz.save()

        autorisatie_oz = applicatie_oz.autorisaties.first()
        autorisatie_on = applicatie_on.autorisaties.first()

        autorisatie_oz.zaaktype = ZAAKTYPE3
        autorisatie_oz.save()
        autorisatie_on.zaaktype = ZAAKTYPE4
        autorisatie_on.save()

        catalogus_autorisatie_oz = applicatie_oz.catalogusautorisatie_set.first()

        catalogus_autorisatie_oz.max_vertrouwelijkheidaanduiding = (
            VertrouwelijkheidsAanduiding.openbaar
        )
        catalogus_autorisatie_oz.save()

        # Overwrite the changes
        AuthorizationConfigurationStep().configure()

        self.assertEqual(JWTSecret.objects.count(), 2)
        self.assertEqual(Applicatie.objects.count(), 2)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 1)

        jwt_secret_oz = JWTSecret.objects.get(identifier="open-zaak")
        self.assertEqual(jwt_secret_oz.secret, "oz-secret")

        jwt_secret_on = JWTSecret.objects.get(identifier="open-notificaties")
        self.assertEqual(jwt_secret_on.secret, "on-secret")

        applicatie_oz = Applicatie.objects.get(client_ids=["open-zaak"])

        autorisatie_oz = applicatie_oz.autorisaties.get()
        self.assertEqual(autorisatie_oz.component, ComponentTypes.zrc)
        self.assertEqual(
            autorisatie_oz.scopes,
            [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_ALLES_LEZEN)],
        )
        self.assertEqual(autorisatie_oz.zaaktype, ZAAKTYPE1)
        self.assertEqual(
            autorisatie_oz.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.geheim,
        )

        catalogus_autorisatie_oz = applicatie_oz.catalogusautorisatie_set.get()
        self.assertEqual(catalogus_autorisatie_oz.catalogus, self.catalogus)
        self.assertEqual(catalogus_autorisatie_oz.component, ComponentTypes.drc)
        self.assertEqual(
            catalogus_autorisatie_oz.scopes, [str(SCOPE_DOCUMENTEN_ALLES_LEZEN)]
        )
        self.assertEqual(
            catalogus_autorisatie_oz.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        applicatie_on = Applicatie.objects.get(client_ids=["open-notificaties"])

        autorisatie_on = applicatie_on.autorisaties.get()
        self.assertEqual(autorisatie_on.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie_on.scopes, [str(SCOPE_ZAKEN_ALLES_LEZEN)])
        self.assertEqual(autorisatie_on.zaaktype, ZAAKTYPE2)
        self.assertEqual(
            autorisatie_on.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_configure_overwrite_with_existing_other_configuration(self):
        """
        Running `.configure` should preserve data that was not present in the fixture
        """
        AuthorizationConfigurationStep().configure()

        applicatie_oz, _ = Applicatie.objects.all()

        new_autorisatie = AutorisatieFactory.create(
            applicatie=applicatie_oz,
            component=ComponentTypes.brc,
            besluittype="http://foo.bar",
            scopes=["besluiten.lezen"],
        )

        new_applicatie = ApplicatieFactory.create()
        new_catalogus_auth = CatalogusAutorisatieFactory.create(
            applicatie=new_applicatie
        )

        # Overwrite the changes
        AuthorizationConfigurationStep().configure()

        # Check if the added data that was not present in the .yaml file still exists
        new_autorisatie.refresh_from_db()
        new_applicatie.refresh_from_db()
        new_catalogus_auth.refresh_from_db()

        self.assertEqual(JWTSecret.objects.count(), 2)
        self.assertEqual(Applicatie.objects.count(), 3)
        self.assertEqual(Autorisatie.objects.count(), 3)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 2)

    @override_settings(AUTHORIZATIONS_CONFIG_DELETE_EXISTING=True)
    def test_configure_overwrite_delete_existing_other_configuration(self):
        """
        Running `.configure` with AUTHORIZATIONS_CONFIG_DELETE_EXISTING=True should
        delete data that was not present in the fixture
        """
        AuthorizationConfigurationStep().configure()

        applicatie_oz, _ = Applicatie.objects.all()

        new_autorisatie = AutorisatieFactory.create(
            applicatie=applicatie_oz,
            component=ComponentTypes.brc,
            besluittype="http://foo.bar",
            scopes=["besluiten.lezen"],
        )

        new_applicatie = ApplicatieFactory.create()
        new_catalogus_auth = CatalogusAutorisatieFactory.create(
            applicatie=new_applicatie
        )

        # Overwrite the changes
        AuthorizationConfigurationStep().configure()

        # Check if the added data that was not present in the .yaml file still exists
        with self.assertRaises(Autorisatie.DoesNotExist):
            new_autorisatie.refresh_from_db()
        with self.assertRaises(Applicatie.DoesNotExist):
            new_applicatie.refresh_from_db()
        with self.assertRaises(CatalogusAutorisatie.DoesNotExist):
            new_catalogus_auth.refresh_from_db()

        self.assertEqual(JWTSecret.objects.count(), 2)
        self.assertEqual(Applicatie.objects.count(), 2)
        self.assertEqual(Autorisatie.objects.count(), 2)
        self.assertEqual(CatalogusAutorisatie.objects.count(), 1)

    @override_settings(AUTHORIZATIONS_CONFIG_DELETE_EXISTING=True)
    def test_configure_delete_existing_config_not_allowed_if_other_steps_load_auth_data(
        self,
    ):
        """
        Running `.configure` with AUTHORIZATIONS_CONFIG_DELETE_EXISTING=True should raise an error
        if other steps that load authorization data (secrets/applicaties) are enabled
        """
        for setting_name in DISALLOWED_SETTINGS:
            with self.subTest(setting_name=setting_name), override_settings(
                **{setting_name: True}
            ):
                with self.assertRaises(ConfigurationRunFailed):
                    AuthorizationConfigurationStep().configure()

    def test_is_configured(self):
        configuration = AuthorizationConfigurationStep()

        self.assertFalse(configuration.is_configured())

        configuration.configure()

        # Modifying these attribute should not affect `is_configured`
        secret_oz, secret_on = JWTSecret.objects.all()

        secret_oz.secret = "modified-secret"
        secret_oz.save()
        secret_on.secret = "modified-secret"
        secret_on.save()

        applicatie_oz, applicatie_on = Applicatie.objects.all()
        applicatie_oz.label = "Open Zaak"
        applicatie_oz.save()
        applicatie_oz.label = "Open Notificaties"
        applicatie_oz.save()

        autorisatie_oz = applicatie_oz.autorisaties.first()
        autorisatie_on = applicatie_on.autorisaties.first()

        autorisatie_oz.zaaktype = ZAAKTYPE3
        autorisatie_oz.save()
        autorisatie_on.zaaktype = ZAAKTYPE4
        autorisatie_on.save()

        catalogus_autorisatie_oz = applicatie_oz.catalogusautorisatie_set.first()

        catalogus_autorisatie_oz.max_vertrouwelijkheidaanduiding = (
            VertrouwelijkheidsAanduiding.openbaar
        )
        catalogus_autorisatie_oz.save()

        self.assertTrue(configuration.is_configured())
