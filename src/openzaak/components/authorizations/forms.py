from django import forms

from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret


class ApplicatieForm(forms.ModelForm):
    class Meta:
        model = Applicatie
        # removed `client_ids arrayfield - replaced by and inline
        # doing stuff with JWTSecret
        fields = ("uuid", "label", "heeft_alle_autorisaties")


class CredentialsBaseFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance")
        queryset = kwargs.pop("queryset")
        kwargs.pop("save_as_new", None)

        if instance.client_ids:
            kwargs["queryset"] = queryset.filter(identifier__in=instance.client_ids)
        else:
            kwargs["queryset"] = queryset.none()

        self.instance = instance

        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        commit = kwargs.get("commit", True)
        creds = super().save(*args, **kwargs)

        old_identifiers = {
            form.instance.pk: form.initial["identifier"]
            for form in self.forms
            if form.instance.pk and "identifier" in form.initial
        }

        for cred in self.deleted_objects:
            self.instance.client_ids.remove(cred.identifier)

        for cred, changed in self.changed_objects:
            if "identifier" not in changed:
                continue

            old_identifier = old_identifiers[cred.id]
            self.instance.client_ids.remove(old_identifier)
            self.instance.client_ids.append(cred.identifier)

        for cred in creds:
            if cred.identifier in self.instance.client_ids:
                continue
            self.instance.client_ids.append(cred.identifier)

        if commit:
            self.instance.save(update_fields=["client_ids"])
        return creds


CredentialsFormSet = forms.modelformset_factory(
    JWTSecret,
    formset=CredentialsBaseFormSet,
    fields=("identifier", "secret"),
    extra=1,
    can_delete=True,
)
