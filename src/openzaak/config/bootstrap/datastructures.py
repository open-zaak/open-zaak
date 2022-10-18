# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from dataclasses import dataclass


@dataclass
class Output:
    id: str  # must be unique!
    title: str
    data: dict

    def __str__(self):
        bits = [f"{self.title} (id: {self.id}):",] + [
            f"  * {key}: {value}" for key, value in self.data.items()
        ]
        return "\n".join(bits)

    def as_json(self) -> dict:
        return {self.id: {"title": self.title, "data": self.data}}
