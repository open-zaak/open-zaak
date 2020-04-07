import React, {useContext, useState} from "react";
import {SelectInput} from "./select";
import {TextInput} from "../../forms/inputs";
import {ConstantsContext} from "./context";


function AuthType(props) {
    const { index, data } = props;
    const { values, errors } = data;

    const { authTypeChoices } = useContext(ConstantsContext);
    const [ selectedAuthType, setSelectedAuthType ] = useState(values.auth_type);

    const id_prefix = (field) => `id_form-${index}-${field}`;
    const name_prefix = (field) => `form-${index}-${field}`;


    const AuthField = (props) => {
        const { name, value, label, errors} = props;

        return (
            <div className='form-group row'>
                <label
                    htmlFor={id_prefix(name)}
                    className='col-form-label col-form-label-sm col'
                >{label}:
                </label>
                <div className='col'>
                    <TextInput
                        id={id_prefix(name)}
                        name={name_prefix(name)}
                        initial={value}
                        classes='form-control form-control-sm'
                        errors={errors}
                    />
                </div>
            </div>
        )
    };

    return (
        <div className='form-group col'>
            <SelectInput
                choices={authTypeChoices}
                name={name_prefix('auth_type')}
                initialValue={values.auth_type}
                classes='form-control'
                errors={errors.auth_type}
                onChange={(auth_type) => setSelectedAuthType(auth_type)}
            />

            {(selectedAuthType === 'zgw') ?
                (<div className='pt-3'>
                    <AuthField
                        name='client_id'
                        value={values.client_id}
                        label='Client ID'
                        errors={errors.client_id}
                    />
                    <AuthField
                        name='secret'
                        value={values.secret}
                        label='Secret'
                        errors={errors.secret}
                    />
                    <AuthField
                        name='user_id'
                        value={values.user_id}
                        label='User ID'
                        errors={errors.user_id}
                    />
                    <AuthField
                        name='user_representation'
                        value={values.user_representation}
                        label='User representation'
                        errors={errors.user_representation}
                    />
                </div>) : null}

            {(selectedAuthType === 'api_key') ?
                (<div className='pt-3'>
                    <AuthField
                        name='header_key'
                        value={values.header_key}
                        label='Header'
                        errors={errors.header_key}
                    />
                    <AuthField
                        name='header_value'
                        value={values.header_value}
                        label='Value'
                        errors={errors.header_value}
                    />
                </div>) : null}

        </div>
    );
}


export { AuthType };
