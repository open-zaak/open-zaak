from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from solo.admin import SingletonModelAdmin

from .models import ADFSConfig


@admin.register(ADFSConfig)
class ADFSConfigAdmin(SingletonModelAdmin):
    fieldsets = (
        (_("Activation"), {"fields": ("enabled",),}),
        (_("On-premise"), {"fields": ("server",),}),
        (_("Azure AD"), {"fields": ("tenant_id",),}),
        (
            _("Common settings (on-premise and Azure)"),
            {
                "fields": (
                    "client_id",
                    "relying_party_id",
                    "claim_mapping",
                    "username_claim",
                ),
            },
        ),
    )
