from django.contrib.admin.widgets import ManyToManyRawIdWidget


class CatalogusFilterM2MRawIdWidget(ManyToManyRawIdWidget):
    def __init__(self, *args, **kwargs):
        self.catalogus_pk = kwargs.pop("catalogus_pk")
        super().__init__(*args, **kwargs)

    def url_parameters(self):
        params = super().url_parameters()
        if self.catalogus_pk:
            params["catalogus__exact"] = self.catalogus_pk
        return params
