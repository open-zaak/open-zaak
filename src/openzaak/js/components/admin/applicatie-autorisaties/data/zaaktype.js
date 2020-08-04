// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
class ZaakType {
    constructor({id, uuid, identificatie, omschrijving, concept, versiedatum}) {
        Object.assign(
            this,
            {id, uuid, identificatie, omschrijving, concept, versiedatum}
        );
    }

    get str() {
        const version = this.concept ? 'CONCEPT' : this.versiedatum;
        return `${this.omschrijving} (${version})`;
    }
}

export { ZaakType };
