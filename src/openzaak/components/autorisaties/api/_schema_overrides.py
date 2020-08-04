# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import OrderedDict

from openzaak.utils.schema import AutoSchema


class ApplicatieConsumerAutoSchema(AutoSchema):
    def _get_error_responses(self) -> OrderedDict:
        assert self.view.action == "consumer"

        old_action = self.view.action

        self.view.action = "retrieve"
        responses = super()._get_error_responses()
        self.view.action = old_action

        return responses
