import React, {useContext, useState} from "react";
import {TextInput, CheckboxInput, CheckBoxInputBS} from "../../forms/inputs";
import {API_TYPES} from "../../forms/constants";
import {SelectInput} from "./select";
import {ConstantsContext} from "./context";
import {AuthType} from "./auth-type";

function getInitialOrganization (nlx_url, outway) {
    if (!outway || !nlx_url || !nlx_url.startsWith(outway)) {
        return '';
    }
    const path = nlx_url.slice(outway.length);
    return path.split('/')[0];
}


function ExternalForm(props) {
    const { index, data } = props;
    const { values, errors } = data;

    const id_prefix = (field) => `id_form-${index}-${field}`;
    const name_prefix = (field) => `form-${index}-${field}`;

    // nlx calculation
    const { nlxOutway, nlxChoices } = useContext(ConstantsContext);
    const [ isNlx, toggleNlx ] = useState(Boolean(values.nlx));
    const initialOrganization = getInitialOrganization(values.nlx, nlxOutway);
    const [ selectedOrganization, setSelectedOrganization ] = useState(initialOrganization);
    const [ selectedService, setSelectedService ] = useState(values.nlx);
    const organizationChoices = Object.keys(nlxChoices).map((value) => [value, value]);
    const services = nlxChoices[selectedOrganization];
    const serviceChoices = selectedOrganization
        ? Object.keys(services).map((service) => [service, services[service].service_name])
        : [];

    return (
        <div className='form-group row'>
             <input type="hidden" name={name_prefix('id')} defaultValue={ values.id } />
            {/*label*/}
            <div className='form-group col'>
                <TextInput
                    id={id_prefix('label')}
                    name={name_prefix('label')}
                    initial={values.label}
                    classes='form-control'
                    errors={errors.label}
                />
            </div>

            {/*api_type*/}
            <div className='form-group col'>
                <SelectInput
                    choices={API_TYPES}
                    name={name_prefix('api_type')}
                    initialValue={values.api_type}
                    classes='form-control'
                    errors={errors.api_type}
                />
            </div>

            {/*api_root*/}
            <div className='form-group col'>
                <TextInput
                    id={id_prefix('api_root')}
                    name={name_prefix('api_root')}
                    initial={values.api_root}
                    classes='form-control'
                    errors={errors.api_root}
                />
            </div>

            {/*nlx*/}
            <div className='form-group col'>
                <div className='pt-1'>
                <CheckBoxInputBS
                    name={name_prefix('is_nlx')}
                    value={'is_nlx'}
                    label={'Use NLX?'}
                    id={id_prefix('is_nlx')}
                    checked={isNlx}
                    onChange={() => toggleNlx(!isNlx)}
                />
                </div>

                {(isNlx) ? (
                    <div className='form-group pt-3'>
                        <label
                            htmlFor={id_prefix('nlx_organizations')}
                            className='col-form-label col-form-label-sm'
                        >Organization:</label>
                        <SelectInput
                            choices={organizationChoices}
                            name={name_prefix('nlx_organizations')}
                            id={id_prefix('nlx_organizations')}
                            initialValue={selectedOrganization}
                            classes='form-control form-control-sm'
                            onChange={(organization) => setSelectedOrganization(organization)}
                        />

                        <label
                            htmlFor={id_prefix('nlx')}
                            className='col-form-label col-form-label-sm'
                        >Service:</label>
                        <SelectInput
                            choices={serviceChoices}
                            name={name_prefix('nlx')}
                            id={id_prefix('nlx')}
                            initialValue={selectedService}
                            classes='form-control form-control-sm'
                            onChange={(service) => setSelectedService(service)}
                        />

                    </div>
                    ): null
                }
            </div>

            {/*OAS*/}
            <div className='form-group col'>
                <TextInput
                    id={id_prefix('oas')}
                    name={name_prefix('oas')}
                    initial={values.oas}
                    classes='form-control'
                    errors={errors.oas}
                />
            </div>

            {/*auth_type*/}
            <AuthType index={index} data={data} />

        </div>
    );
}

ExternalForm.defaultProps = {
    data: {errors: {}, values: {}}
};

export { ExternalForm };
