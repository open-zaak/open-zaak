import { ZaakType } from './zaaktype';
import { InformatieObjectType } from './informatieobjecttype';
import { BesluitType } from './besluittype';

class Catalogus {
    constructor({ id, _admin_name, uuid, domein, zaaktypen, informatieobjecttypen, besluittypen }) {
        zaaktypen = zaaktypen.map(zt => new ZaakType(zt));
        informatieobjecttypen = informatieobjecttypen.map(iot => new InformatieObjectType(iot));
        besluittypen = besluittypen.map(bt => new BesluitType(bt));

        Object.assign(
            this,
            {
                id,
                _admin_name,
                uuid,
                domein,
                zaaktypen,
                informatieobjecttypen,
                besluittypen
            }
        );
    }

    get str() {
        return this._admin_name;
    }
}


export { Catalogus };
