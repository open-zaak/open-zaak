// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
// See vng_api_common.constants.ComponentTypes
const COMPONENT_CHOICES = [
    ["ac", "Autorisaties API"],
    ["nrc", "Notificaties API"],
    ["zrc", "Zaken API"],
    ["ztc", "Catalogi API"],
    ["drc", "Documenten API"],
    ["brc", "Besluiten API"],
];

// See zgw_consumers.constants.ApiTypes
const API_TYPES = COMPONENT_CHOICES.concat([
    ["kic", "Klantinteracties API"],
    ["orc", "Overige"],
]);

export { COMPONENT_CHOICES, API_TYPES };
