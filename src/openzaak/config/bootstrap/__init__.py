# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Implement utilities to bootstrap the configuration.

A fresh Open Zaak installation needs to be configured before it can be used,
with connections to the Notifications API amongs others.

This module exposes the helpers for every bootstrap part. Every part needs to be
implement such that it's idempotent and can be run mulitple times, e.g. as part of
a container orchestration tool.

See also: :ref:`installation_configuration`.

Configuration aspects:

- [x] Configure the canonical domain: sets the current Site options. Note that this
      should ideally signal other instances (django bug!).

      TODO: include ``settings.ENVIRONMENT`` in the site name once it's configurable
      from the environment.

- [x] Notifications API
    - Open Zaak MAY provide the Autorisaties API used by the Notifications API, this
      requires an application with the appropriate scopes to be configured so that
      Open Zaak is allowed to publish notifications to the Notifications API.

    - Open Zaak is a client of the notifications API and thus requires credentials.
      These credentials need to be configured in the Notifications API to be used.

    - Specify the API root of the Notifications API -> must update_or_create the
      appropriate services with the credentials

    - When Open Zaak provides the Autorisaties API for the Notifications API, an
      application needs to be created for the Notifications API with the appropriate
      scopes so that the Notifications API can query the applications/permissions of
      a given client ID. (SCOPE_AUTORISATIES_LEZEN)

- [ ] Create a demo API token and make a test request?

- [ ] Configure NLX
"""
