from django.utils.translation import ugettext_lazy as _


def mark_experimental(text):
    warning_msg = _(
        "Warning: this feature is experimental and not part of the API standard"
    )
    return "{} **{}**".format(text, warning_msg)
