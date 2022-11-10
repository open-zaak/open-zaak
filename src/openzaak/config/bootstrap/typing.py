# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import List, Protocol

from .datastructures import Output


class ConfigurationProtocol(Protocol):
    """
    Define the base protocol for configuration factories.
    """

    def configure(self) -> List[Output]:
        """
        Make the necessary configuration changes to reach the desired state.
        """
        ...

    def test_configuration(self) -> List[Output]:
        """
        Test the provided configuration parameters.

        :raises: :class:`openzaak.config.bootstrap.exceptions.SelfTestFailure` if a
          configuration aspect was found to be faulty.
        """
        ...
