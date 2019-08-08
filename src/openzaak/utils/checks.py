from django.core.checks import Error, register
from django.forms import ModelForm


def get_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from get_subclasses(subclass)
        yield subclass


@register()
def check_modelform_exclude(app_configs, **kwargs):
    """
    Check that ModelForms use Meta.fields instead of Meta.exclude.

    ModelForm.Meta.exclude is dangerous because it doesn't protect against
    fields that are added later. Explicit white-listing is safer and prevents
    bugs such as IMA #645.

    This check piggy-backs on all form modules to be imported during Django
    startup. It won't cover forms that are defined on the fly such as in
    formset factories.
    """
    errors = []

    for form in get_subclasses(ModelForm):
        # ok, fields is defined
        if form._meta.fields or getattr(form.Meta, 'fields', None):
            continue

        # no `.fields` defined, so scream loud enough to prevent this
        errors.append(Error(
            'ModelForm %s.%s with Meta.exclude detected, this is a bad practice' % (form.__module__, form.__name__),
            hint='Use ModelForm.Meta.fields instead',
            obj=form,
            id='utils.E001'
        ))

    return errors
