from django.contrib import admin

from vng_api_common.authorizations.models import AuthorizationsConfig

admin.site.unregister(AuthorizationsConfig)
