# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _


class DocumentBackendNotImplementedError(NotImplementedError):
    """The functionality for this backend is not implemented yet"""

    def __init__(self, backend_value):
        super().__init__(
            _(
                "The functionality for this backend '{backend_value}' is not implemented yet"
            ).format(backend_value=backend_value),
        )
