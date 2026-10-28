# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
class ListFilterByAuthorizationsMixin:
    """
    Filter list-action data by the authorizations configured.

    Authorizations configured for a client/consumer have a run-time effect
    in _which_ data is effectively exposed. This ``get_queryset``
    implementation facilitates it in a conventional way.

    For this to be effective, the underlying model must have a queryset
    method ``filter_for_authorizations``, which is provided by
    :class:`openzaak.utils.query.LooseFkAuthorizationsFilterMixin`
    """

    def get_queryset(self):
        base = super().get_queryset()

        # django-loose-fk calls get_queryset on viewsets to resolve URLs to resources
        # and in this case the request has no jwt_auth set
        if not hasattr(self.request, "jwt_auth"):
            return base

        if self.action in ["retrieve", "create", "destroy", "update", "partial_update"]:
            # Permission for these actions on singular items is checked in AuthRequired
            # and AuthScopesRequired (src/openzaak/utils/permissions.py)
            # and should 403 if the resource exists, not 404 (which happens if we return
            # an empty filtered queryset here)
            return base

        # get the auth apps that are relevant for this particular request
        apps = self.request.jwt_auth.applicaties
        component = base.model._meta.app_label

        # Autorisaties API 1.1.0 introduced `alleen_is_gereed_voor_publicatie`
        # When enabled, only include documents with `is_gereed_voor_publicatie=True`
        if (
            component == "documenten"
            and any(app.alleen_is_gereed_voor_publicatie for app in apps)
        ):
            base = base.filter(is_gereed_voor_publicatie=True)

        # as soon as there's one matching app that gives you all permissions,
        # you're good - no further detailed data filtering is applied
        if any(app.heeft_alle_autorisaties for app in apps):
            return base

        scope_needed = self.required_scopes[self.action]
        authorizations = self.request.jwt_auth.get_autorisaties(component)
        catalogus_authorizations = self.request.jwt_auth.get_catalogus_autorisaties(
            component
        )
        return base.filter_for_authorizations(
            scope_needed, authorizations, catalogus_authorizations
        )
