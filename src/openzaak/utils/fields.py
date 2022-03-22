# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS

from relativedeltafield import RelativeDeltaField

from openzaak.forms.fields import RelativeDeltaField as RelativeDeltaFormField


class DurationField(RelativeDeltaField):
    def formfield(self, form_class=None, **kwargs):
        if form_class is None:
            form_class = RelativeDeltaFormField
        return super().formfield(form_class=form_class, **kwargs)


# register the override, as the upstream RelativeDeltaField registers its own admin
# form field override as well.
FORMFIELD_FOR_DBFIELD_DEFAULTS[DurationField] = {"form_class": RelativeDeltaFormField}
