# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.db import models


class OrderedTextChoices(models.TextChoices):
    """
    add order for choices and related SQL case expression
    """

    @classmethod
    def get_order_expression(cls, field_name):
        whens = []
        for order, value in enumerate(cls.values):
            whens.append(
                models.When(**{field_name: value, "then": models.Value(order)})
            )
        return models.Case(*whens, output_field=models.IntegerField())

    @classmethod
    def get_choice_order(cls, value) -> int | None:
        orders = {val: order for order, val in enumerate(cls.values)}
        return orders.get(value)
