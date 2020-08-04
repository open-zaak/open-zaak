// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React from "react";
import {CheckBoxInputLabel, TextInput} from "../../../forms/inputs";
import {API_TYPES} from "../../../forms/constants";
import {SelectInput} from "./select";
import {AuthType} from "./auth-type";
import {Nlx} from "./nlx";


function ExternalForm(props) {
    const { index, data } = props;
    const { values, errors } = data;

    const id_prefix = (field) => `id_form-${index}-${field}`;
    const name_prefix = (field) => `form-${index}-${field}`;
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
                    classes="external-form__field--wide"
                />
            </td>

            {/*api_type*/}
            <td className='external-form__field'>
                <SelectInput
                    choices={API_TYPES}
                    name={name_prefix('api_type')}
                    initialValue={values.api_type}
                    errors={errors.api_type}
                    classes="external-form__field--wide"
                />
            </td>

            {/*api_root*/}
            <td className='external-form__field'>
                <TextInput
                    id={id_prefix('api_root')}
                    name={name_prefix('api_root')}
                    initial={values.api_root}
                    errors={errors.api_root}
                    classes="external-form__field--wide"
                />
            </td>

            {/*nlx*/}
            <td className='external-form__field'>
                <Nlx index={index} data={data} />
            </td>

            {/*OAS*/}
            <td className='external-form__field'>
                <TextInput
                    id={id_prefix('oas')}
                    name={name_prefix('oas')}
                    initial={values.oas}
                    errors={errors.oas}
                    classes="external-form__field--wide"
                />
            </td>

            {/*auth_type*/}
            <td className='external-form__field'>
                <AuthType index={index} data={data} />
            </td>

            {/*delete*/}
            <td className='external-form__field'>
                <CheckBoxInputLabel
                    name={name_prefix('DELETE')}
                    value={'can_delete'}
                    id={id_prefix('DELETE')}
                />
            </td>


        </tr>
    );
}

ExternalForm.defaultProps = {
    data: {errors: {}, values: {}}
};

export { ExternalForm };
