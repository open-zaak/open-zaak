from django.urls import include, path
from django.views.generic.base import TemplateView

app_name = 'zrc'

urlpatterns = [
    path('api/', include('openzaak.zrc.api.urls')),

    # Simply show the master template.
    path('', TemplateView.as_view(template_name='index.html'), name='main'),
]
