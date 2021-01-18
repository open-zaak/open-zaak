# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Optional

from requests_mock import Mocker


def mock_pand_get(m: Mocker, url: str, self_url: Optional[str] = None) -> None:
    self_url = self_url or url
    m.get(
        url,
        json={
            "identificatiecode": "0003100000118018",
            "oorspronkelijkBouwjaar": 1965,
            "status": "PandInGebruik",
            "_links": {"self": {"href": self_url,},},
            "_embedded": {
                "geometrie": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [5.3329181, 52.113041],
                            [5.3512001, 52.11283],
                            [5.3510284, 52.10234],
                            [5.3329181, 52.113041],
                        ]
                    ],
                },
            },
        },
    )
