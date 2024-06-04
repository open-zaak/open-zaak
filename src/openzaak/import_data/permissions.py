# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from openzaak.import_data.models import ImportTypeChoices
from openzaak.utils.permissions import AuthRequired


class ImportAuthRequired(AuthRequired):
    def get_component(self, view) -> str:
        importer_type = view.import_type
        return ImportTypeChoices.get_component_from_choice(importer_type)
