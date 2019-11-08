"""
Integrations of selectielijst API into Django admin.
"""
from typing import Any, Dict, List

from django import forms
from django.db.models import Field
from django.http import HttpRequest

from zds_client import Client

from openzaak.utils.decorators import cache


@cache("selectielijst:procestypen", timeout=60 * 60 * 24)
def get_procestypen() -> List[Dict[str, Any]]:
    """
    Fetch a list of Procestypen.
    """
    client = Client("selectielijst")
    return client.list("procestype")


def get_procestype_field(
    db_field: Field, request: HttpRequest, **kwargs
) -> forms.ChoiceField:
    choices = (
        (procestype["url"], f"{procestype['nummer']} - {procestype['naam']}",)
        for procestype in get_procestypen()
    )

    return forms.ChoiceField(
        label=db_field.verbose_name.capitalize(),
        choices=choices,
        required=False,
        help_text=db_field.help_text,
    )
