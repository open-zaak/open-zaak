# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from openzaak.components.besluiten.tests.test_besluitinformatieobjecten import (
    BesluitInformatieObjectAPITests as _BesluitInformatieObjectAPITests,
    ExternalDocumentDestroyTests as _ExternalDocumentDestroyTests,
    ExternalDocumentsAPITests as _ExternalDocumentsAPITests,
    ExternalDocumentsAPITransactionTests as _ExternalDocumentsAPITransactionTests,
    ExternalInformatieObjectAPITests as _ExternalInformatieObjectAPITests,
)


class BesluitInformatieObjectAPITests(_BesluitInformatieObjectAPITests):
    NAMESPACE = "zaken"


class ExternalDocumentsAPITests(_ExternalDocumentsAPITests):
    NAMESPACE = "zaken"


class ExternalDocumentsAPITransactionTests(_ExternalDocumentsAPITransactionTests):
    NAMESPACE = "zaken"


class ExternalInformatieObjectAPITests(_ExternalInformatieObjectAPITests):
    NAMESPACE = "zaken"


class ExternalDocumentDestroyTests(_ExternalDocumentDestroyTests):
    NAMESPACE = "zaken"
