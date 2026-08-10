# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.utils.functional import empty

from ..storage import documenten_storage


@receiver(setting_changed)
def update_filefield_storage(setting, **kwargs):
    # This signal is also defined by `django-privates` but overridden here, because
    # django-privates only clears the private_media_storage object and Open Zaak
    # has its own lazy object to define the storage backend
    if setting == "STORAGES":
        documenten_storage._wrapped = empty  # type: ignore
