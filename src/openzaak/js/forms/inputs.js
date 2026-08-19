// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {ErrorList} from "./error-list";


const Input = (props) => {
    const { type, name, value, label, i, checked, onChange } = props;
    const id = `id_${name}_${i}`;
    return (
        <label htmlFor={id}>
            <input
                type={type}
                name={name}
                value={value}
                id={id}
                checked={checked}
                onChange={ (event) => onChange(event, value) }
            />
            &nbsp;{label}
        </label>
    );
};

Input.propTypes = {
    type: PropTypes.oneOf(["radio", "checkbox"]),
    name: PropTypes.string.isRequired,
    value: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    i: PropTypes.number.isRequired,
    checked: PropTypes.bool.isRequired,
    onChange: PropTypes.func,
};


const RadioInput = (props) => {
    return <Input type="radio" {...props} />;
};

const CheckboxInput = (props) => {
    return <Input type="checkbox" {...props} />;
};


// labeled checkbox
const CheckBoxInputLabel = (props) => {
    const { type, name, value, id, label, checked, onChange, disabled } = props;
    return (
        <>
            <input
                type="checkbox"
                id={id}
                name={name}
                value={value}
                checked={checked}
                onChange={ (event) => onChange(event, value) }
                disabled={disabled}
            />
            <label htmlFor={id}>{label}</label>
        </>
    );
};


const TextInput = (props) => {
    // `onChange` is used to update the controlledValue
    const { id, name, initial, value: controlledValue, classes, errors, onChange } = props;
    const [value, setValue] = useState(initial || "");
    const [_errors, setErrors] = useState(errors);
    const valueProps = controlledValue === undefined
        ? {defaultValue: value}
        : {value: controlledValue};

    return (
        <>
            <ErrorList errors={_errors} />
            <input
                type="text"
                name={name}
                id={id}
                onChange={(event) => {
                    const newValue = event.target.value;
                    setValue(newValue);
                    setErrors([]);

                    if (onChange) {
                        onChange(newValue);
                    }
                }}
                {...valueProps}
                className={classes}
            ></input>
        </>
    );
};


export { CheckboxInput, CheckBoxInputLabel, RadioInput, TextInput };
