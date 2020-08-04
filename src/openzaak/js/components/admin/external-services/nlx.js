// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React, {useContext, useState} from "react";
import {CheckBoxInputLabel} from "../../../forms/inputs";
import {SelectInput} from "./select";
import {ConstantsContext} from "./context";

function getInitialOrganization (choices, nlx_url, outway) {
    if (!choices || !choices.length) {
        return '';
    }
    if (!outway || !nlx_url || !nlx_url.startsWith(outway)) {
        return choices[0][0];
    }
    const path = nlx_url.slice(outway.length);
    return path.split('/')[0];
}


function Nlx(props) {
    const { index, data } = props;
    const { values, errors } = data;

    const id_prefix = (field) => `id_form-${index}-${field}`;
    const name_prefix = (field) => `form-${index}-${field}`;

    const { nlxOutway, nlxChoices } = useContext(ConstantsContext);
    const [ isNlx, toggleNlx ] = useState(Boolean(values.nlx));
    const isNlxDisabled = !nlxOutway;

    // calculations for organization select
    const organizationChoices = Object.keys(nlxChoices).map((value) => [value, value]);
    const initialOrganization = getInitialOrganization(organizationChoices, values.nlx, nlxOutway);
    const [ selectedOrganization, setSelectedOrganization ] = useState(initialOrganization);

    // calculations for service select
    const [ selectedService, setSelectedService ] = useState(values.nlx);
    const services = nlxChoices[selectedOrganization];
    const serviceChoices = selectedOrganization
        ? Object.keys(services).map((service) => [service, services[service].service_name])
        : [];

    return (
        <div title={isNlxDisabled ? "NLW outway must be set up" : null}>
            <CheckBoxInputLabel
                name={name_prefix('is_nlx')}
                value={'is_nlx'}
                label={'Use NLX?'}
                id={id_prefix('is_nlx')}
                checked={isNlx}
                onChange={() => toggleNlx(!isNlx)}
                disabled={isNlxDisabled}
            />

            {(isNlx && !isNlxDisabled) ? (
                <>
                    <div className='external-form__group'>
                        <label
                            htmlFor={id_prefix('nlx_organizations')}
                            className='external-form__label'
                        >Organization:</label>
                        <SelectInput
                            choices={organizationChoices}
                            name={name_prefix('nlx_organizations')}
                            id={id_prefix('nlx_organizations')}
                            initialValue={selectedOrganization}
                            onChange={(organization) => setSelectedOrganization(organization)}
                            classes="external-form__field--wide"
                        />
                    </div>

                    <div className='external-form__group'>
                        <label
                            htmlFor={id_prefix('nlx')}
                            className='external-form__label'
                        >Service:</label>
                        <SelectInput
                            choices={serviceChoices}
                            name={name_prefix('nlx')}
                            id={id_prefix('nlx')}
                            initialValue={selectedService}
                            onChange={(service) => setSelectedService(service)}
                            classes="external-form__field--wide"
                        />
                    </div>
                </>
                ): null
            }
        </div>
    );
}

export {Nlx};
