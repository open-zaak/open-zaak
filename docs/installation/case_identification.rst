===================
Case Identification
===================

Open Zaak has multiple ``zaak identificatie`` generator options which are used when creating a zaak or when reserving a zaaknummer.
A generator can be selected using ``ZAAK_IDENTIFICATIE_GENERATOR`` see :ref:`installation_env_config`.


Standard options
================
* ``use-start-datum-year`` (default), uses the zaak start_datum for the identification. (ZAAK-2026-0000000001)
* ``use-creation-year`` (default), uses the current year when the zaak is created (or when zaaknummmmer is reserved). (ZAAK-2026-0000000001)

Specialized options
===================
* ``use-uwv-identification`` is a custom zaak identification for the UWV which uses an 11-proef. (A00000006)
