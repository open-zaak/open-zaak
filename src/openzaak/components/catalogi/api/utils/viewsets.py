class FilterSearchOrderingViewSetMixin(object):
    """
    Consult the model options to set filter-, ordering- and search fields.
    """
    def get_model_option(self, attr, default=None):
        if default is None:
            default = []
        return getattr(self.queryset.model._meta, attr, default)

    @property
    def filter_fields(self):
        """
        The fields that can be used as query param, to filter the results.
        """
        return self.get_filter_fields()

    @property
    def ordering_fields(self):
        """
        The fields that can be used in the query param ``?ordering=``
        """
        return self.get_ordering_fields()

    @property
    def search_fields(self):
        """
        The fields that can be used in the query param ``?search=``
        """
        return self.get_search_fields()

    def get_filter_fields(self):
        """
        This function can be overriden to return custom fields.
        """
        return self.get_model_option('filter_fields')

    def get_ordering_fields(self):
        """
        This function can be overriden to return custom fields.
        """
        return self.get_model_option('ordering_fields')

    def get_search_fields(self):
        """
        This function can be overriden to return custom fields.
        """
        return self.get_model_option('search_fields')
