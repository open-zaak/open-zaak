# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os

from django.conf import settings
from django.core.checks import Error, Warning, register
from django.forms import ModelForm
from django.http.request import validate_host

from furl.furl import furl


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
        # Skip forms from third party apps
        if not form.__module__.startswith("openzaak."):
            continue

        # ok, fields is defined
        if form._meta.fields or getattr(form.Meta, "fields", None):
            continue

        # no `.fields` defined, so scream loud enough to prevent this
        errors.append(
            Error(
                "ModelForm %s.%s with Meta.exclude detected, this is a bad practice"
                % (form.__module__, form.__name__),
                hint="Use ModelForm.Meta.fields instead",
                obj=form,
                id="utils.E001",
            )
        )

    return errors


@register
def check_missing_init_files(app_configs, **kwargs):
    """
    Check that all packages have __init__.py files.

    If they don't, the code will still run, but tests aren't picked up by the
    test runner, for example.
    """
    errors = []

    for dirpath, dirnames, filenames in os.walk(settings.DJANGO_PROJECT_DIR):
        dirname = os.path.split(dirpath)[1]
        if dirname == "__pycache__":
            continue

        if "__init__.py" in filenames:
            continue

        extensions = [os.path.splitext(fn)[1] for fn in filenames]
        if ".py" not in extensions:
            continue

        errors.append(
            Warning(
                'Directory "%s" does not contain an `__init__.py` file' % dirpath,
                hint="Consider adding this module to make sure tests are picked up",
                id="utils.W001",
            )
        )

    return errors


@register
def check_openzaak_domain(app_configs, **kwargs):
    if not settings.OPENZAAK_DOMAIN:
        return []

    errors = []

    try:
        parsed = furl(netloc=settings.OPENZAAK_DOMAIN)
    except ValueError:
        invalid_netloc = True
    else:
        invalid_netloc = (
            parsed.scheme or parsed.path or parsed.username or parsed.password
        )

    if invalid_netloc:
        errors.append(
            Error(
                "The OPENZAAK_DOMAIN setting is invalid, it must be a valid DNS name "
                "with an optional port according to the pattern HOST[:PORT].",
                hint="Do not include scheme or path components.",
                id="openzaak.settings.E001",
            )
        )

    else:  # check against ALLOWED_HOSTS
        host = parsed.host.lower()
        if settings.OPENZAAK_REWRITE_HOST and not validate_host(
            host, settings.ALLOWED_HOSTS
        ):
            errors.append(
                Error(
                    f"The OPENZAAK_DOMAIN host ({host}) is not present in the "
                    "ALLOWED_HOSTS setting.",
                    hint=f"Add {host} to the ALLOWED_HOSTS setting.",
                    id="openzaak.settings.E002",
                )
            )

    if settings.OPENZAAK_REWRITE_HOST and settings.USE_X_FORWARDED_HOST:
        errors.append(
            Warning(
                "Setting OPENZAAK_REWRITE_HOST together with USE_X_FORWARDED_HOST causes "
                "the X-Forwarded-Host header to be ignored.",
                hint="Disable USE_X_FORWARDED_HOST or OPENZAAK_REWRITE_HOST",
                id="openzaak.settings.W001",
            )
        )

    return errors


@register
def check_zaak_identificatie_generator(app_configs, **kwargs):
    errors = []

    generator = settings.ZAAK_IDENTIFICATIE_GENERATOR
    options = settings.ZAAK_IDENTIFICATIE_GENERATOR_OPTIONS

    if generator not in options:
        errors.append(
            Error(
                f"`{generator}` is not a valid value for the environment variable ZAAK_IDENTIFICATIE_GENERATOR.",
                hint=f"Set ZAAK_IDENTIFICATIE_GENERATOR to one of the following values: {list(options.keys())}.",
                id="openzaak.settings.E003",
            )
        )

    return errors
