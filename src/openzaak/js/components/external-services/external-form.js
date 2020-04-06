import React, {useContext} from "react";
import {TextInput} from "../../forms/inputs";
import {API_TYPES} from "../../forms/constants";
import {SelectInput} from "./select";
import {ConstantsContext} from "./context";


function ExternalForm(props) {
    const { index, data } = props;
    const { values, errors } = data;

    const { authTypeChoices } = useContext(ConstantsContext);

    const id_prefix = (field) => `id_form-${index}-${field}`;
    const name_prefix = (field) => `form-${index}-${field}`;

    return (
        <div className='form-group row'>
            {/*label*/}
            <div className='form-group col'>
                <TextInput
                    id={id_prefix('label')}
                    name={name_prefix('label')}
                    initial={values.label}
                    classes='form-control'
                />
            </div>

            {/*api_type*/}
            <div className='form-group col'>
                <SelectInput
                    choices={API_TYPES}
                    name={name_prefix('api_type')}
                    initialValue={values.api_type}
                    classes='form-control'
                />
            </div>

            {/*api_root*/}
            <div className='form-group col'>
                <TextInput
                    id={id_prefix('api_root')}
                    name={name_prefix('api_root')}
                    initial={values.api_root}
                    classes='form-control'
                />
            </div>

            {/*nlx*/}
            <div className='form-group col'>
                <TextInput
                    id={id_prefix('nlx')}
                    name={name_prefix('nlx')}
                    initial={values.nlx}
                    classes='form-control'
                />
            </div>

            {/*auth_type*/}
            <div className='form-group col'>
                <SelectInput
                    choices={authTypeChoices}
                    name={name_prefix('auth_type')}
                    initialValue={values.auth_type}
                    classes='form-control'
                />
            </div>
        </div>
    );

}

export { ExternalForm };
