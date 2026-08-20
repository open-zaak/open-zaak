// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React, {useRef, useState} from "react";
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

    const [slug, setSlug] = useState(values.slug ?? "");
    const slugManuallyEdited = useRef(Boolean(values.slug));
    const isCreate = !values.id;

    /**
     * Automatically populates the slug from the label when the slug
     * has not been manually edited and the form is in create mode.
     * @param {string} label
     */
    const handleSlugChange = (label) => {
        if (!isCreate || slugManuallyEdited.current === true) {
            return;
        }

        /*
        * Convert the label into a URL-friendly slug:
        * 1. Convert all characters to lowercase.
        * 2. Remove whitespace from the beginning and end.
        * 3. Replace one or more spaces with a hyphen (-).
        * 4. Remove special characters, keeping only letters, numbers,
        *    underscores, and hyphens.
        * 5. Set the resulting value as the slug.
        */
       const slugLabel = label
                .toLowerCase()
                .trim()
                .replace(/\s+/g, "-")
                .replace(/[^\w-]/g, "");
        setSlug(slugLabel);
    };

    const handleManualSlugChange = (value) => {
        slugManuallyEdited.current = true;
        setSlug(value);
    };

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
                    onChange={handleSlugChange}
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

            {/*slug*/}
            <td className='external-form__field'>
                <TextInput
                    id={id_prefix('slug')}
                    name={name_prefix('slug')}
                    value={slug}
                    errors={errors.slug}
                    onChange={handleManualSlugChange}
                    classes="external-form__field--wide"
                />
            </td>

            {/*nlx*/}
            <td className='external-form__field'>
                <Nlx index={index} data={data} />
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
