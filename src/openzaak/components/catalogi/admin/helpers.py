# all helper classes below are used to able to modify read_only field content

from django.contrib.admin.helpers import (
    AdminField,
    AdminForm as _AdminForm,
    AdminReadonlyField as _AdminReadonlyField,
    Fieldline as _Fieldline,
    Fieldset as _Fieldset,
)


class AdminForm(_AdminForm):
    def __init__(
        self, callback_readonly, *args, **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def __iter__(self):
        for name, options in self.fieldsets:
            yield Fieldset(
                self.callback_readonly,
                self.form,
                name,
                readonly_fields=self.readonly_fields,
                model_admin=self.model_admin,
                **options,
            )


class Fieldset(_Fieldset):
    def __init__(self, callback_readonly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def __iter__(self):
        for field in self.fields:
            yield Fieldline(
                self.callback_readonly,
                self.form,
                field,
                self.readonly_fields,
                model_admin=self.model_admin,
            )


class Fieldline(_Fieldline):
    def __init__(self, callback_readonly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def __iter__(self):
        for i, field in enumerate(self.fields):
            if field in self.readonly_fields:
                yield AdminReadonlyField(
                    self.callback_readonly,
                    self.form,
                    field,
                    is_first=(i == 0),
                    model_admin=self.model_admin,
                )
            else:
                yield AdminField(self.form, field, is_first=(i == 0))


class AdminReadonlyField(_AdminReadonlyField):
    def __init__(self, callback_readonly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def contents(self):
        html_value = super().contents()

        field, obj = self.field["field"], self.form.instance
        if not obj:
            return html_value

        modified_value = self.callback_readonly(field, html_value)
        return modified_value
