class SourceMappingSerializerMixin(object):
    """
    Read the `Meta.source_mapping` attribute and fill the `extra_kwargs` with
    the appropriate `source` argument.
    """
    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()

        source_mapping = getattr(self.Meta, 'source_mapping', None)
        if source_mapping is not None:
            if not isinstance(source_mapping, dict):
                raise TypeError(
                    'The `source_mapping` option must be a dict. '
                    'Got %s.' % type(source_mapping).__name__
                )
            for field_name, source in source_mapping.items():
                kwargs = extra_kwargs.get(field_name, {})
                kwargs['source'] = source
                extra_kwargs[field_name] = kwargs

        return extra_kwargs
