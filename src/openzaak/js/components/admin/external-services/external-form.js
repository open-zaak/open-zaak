import React, {useContext, useState} from "react";
import {TextInput, CheckboxInput, CheckBoxInputBS} from "../../../forms/inputs";
import {API_TYPES} from "../../../forms/constants";
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

    const isEven = (index % 2) === 0;

    return (
        <tr className={`form-row external-form external-form--${isEven ? 'even' : 'odd'}`}>
            <td className='external-form__hidden'>
                <input type="hidden" name={name_prefix('id')} defaultValue={ values.id } />
             </td>

            {/*label*/}
            <td className='external-form__field'>
                <TextInput
                    id={id_prefix('label')}
                    name={name_prefix('label')}
                    initial={values.label}
                    errors={errors.label}
                />
            </td>

            {/*api_type*/}
            <td className='external-form__field'>
                <SelectInput
                    choices={API_TYPES}
                    name={name_prefix('api_type')}
                    initialValue={values.api_type}
                    errors={errors.api_type}
                />
            </td>

            {/*api_root*/}
            <td className='external-form__field'>
                <TextInput
                    id={id_prefix('api_root')}
                    name={name_prefix('api_root')}
                    initial={values.api_root}
                    errors={errors.api_root}
                />
            </td>

            {/*nlx*/}
            <td className='external-form__field'>
                <CheckBoxInputBS
                    name={name_prefix('is_nlx')}
                    value={'is_nlx'}
                    label={'Use NLX?'}
                    id={id_prefix('is_nlx')}
                    checked={isNlx}
                    onChange={() => toggleNlx(!isNlx)}
                />

                {(isNlx) ? (
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
                            />
                        </div>
                    </>
                    ): null
                }
            </td>

            {/*OAS*/}
            <td className='external-form__field'>
                <TextInput
                    id={id_prefix('oas')}
                    name={name_prefix('oas')}
                    initial={values.oas}
                    errors={errors.oas}
                />
            </td>

            {/*auth_type*/}
            <td className='external-form__field'>
                <AuthType index={index} data={data} />
            </td>

        </tr>
    );
}

ExternalForm.defaultProps = {
    data: {errors: {}, values: {}}
};

export { ExternalForm };
