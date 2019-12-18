import { ZaakType } from './zaaktype';

class Catalogus {
    constructor({ id, _admin_name, uuid, domein, zaaktypen }) {
        zaaktypen = zaaktypen.map(zt => new ZaakType(zt));
        Object.assign(
            this,
            { id, _admin_name, uuid, domein, zaaktypen }
        );
    }

    get str() {
        return this._admin_name;
    }
}


export { Catalogus };
