from django.db.models import QuerySet


class BlockChangeMixin:
    @property
    def msg(self):
        return f"This method is forbidden for {self.model.__name__} queryset"

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        raise TypeError(self.msg)

    def bulk_update(self, objs, fields, batch_size=None):
        raise TypeError(self.msg)

    def update(self, **kwargs):
        raise TypeError(self.msg)

    def delete(self):
        raise TypeError(self.msg)
