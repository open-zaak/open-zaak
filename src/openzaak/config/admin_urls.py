from django.urls import path

from .admin_views import NLXConfigView

app_name = 'config'

urlpatterns = [
    path(r'nlx', NLXConfigView.as_view(), name='nlx_config'),
]
