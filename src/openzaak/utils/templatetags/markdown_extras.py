# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django import template

import markdown

register = template.Library()


@register.filter
def markdown_with_anchors(value):
    """
    Converts markdown text to HTML with anchors added to headings.
    """
    return markdown.markdown(value, extensions=["toc", "attr_list", "extra"])
