// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React, {useContext, useState} from "react";
import {SelectInput} from "./select";
import {TextInput} from "../../../forms/inputs";
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
            <div className='external-form__group'>
                <label
                    htmlFor={id_prefix(name)}
                    className='external-form__label'
                >{label}: </label>
                <TextInput
                    id={id_prefix(name)}
                    name={name_prefix(name)}
                    initial={value}
                    errors={errors}
                    classes="external-form__field--wide"
                />
            </div>
        )
    };

    return (
        <>
            <SelectInput
                choices={authTypeChoices}
                name={name_prefix('auth_type')}
                initialValue={values.auth_type}
                errors={errors.auth_type}
                onChange={(auth_type) => setSelectedAuthType(auth_type)}
                classes="external-form__field--wide"
            />

            {(selectedAuthType === 'zgw') ?
                (<>
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
                </>) : null}

            {(selectedAuthType === 'api_key') ?
                (<div>
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

        </>
    );
}


export { AuthType };
