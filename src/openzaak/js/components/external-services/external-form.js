import React, {useContext, useState} from "react";
import {TextInput, CheckboxInput} from "../../forms/inputs";
import {API_TYPES} from "../../forms/constants";
import {SelectInput} from "./select";
import {ConstantsContext} from "./context";
import {AuthType} from "./auth-type";


function ExternalForm(props) {
    const { index, data } = props;
    const { values, errors } = data;

    const { nlxOutway, nlxChoices } = useContext(ConstantsContext);
    const [ isNlx, toggleNlx ] = useState(Boolean(values.nlx));

    const id_prefix = (field) => `id_form-${index}-${field}`;
    const name_prefix = (field) => `form-${index}-${field}`;

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
                <CheckboxInput
                    name={name_prefix('is_nlx')}
                    value={'is_nlx'}
                    label={'Use nlx?'}
                    i={index}
                    checked={isNlx}
                    onChange={() => toggleNlx(!isNlx)}
                />

                {(isNlx) ?
                    <TextInput
                        id={id_prefix('nlx')}
                        name={name_prefix('nlx')}
                        initial={values.nlx}
                        classes='form-control'
                        errors={errors.nlx}
                    /> : null
                }
            </div>

            {/*auth_type*/}
            <AuthType index={index} data={data} />

        </div>
    );

}

export { ExternalForm };
