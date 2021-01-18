// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
class BesluitType {
    constructor({ id, uuid, omschrijving, concept }) {
        Object.assign(
            this,
            { id, uuid, omschrijving, concept }
        );
    }

    get str() {
        const version = this.concept ? ' (CONCEPT)' : '';
        return `${this.omschrijving}${version}`;
    }
}

export { BesluitType };
