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


// checkbox for bootstrap-formatted pages
const CheckBoxInputBS = (props) => {
    const { type, name, value, id, label, checked, onChange, disabled } = props;
    return (
        <div className='form-check'>
            <input
                type="checkbox"
                id={id}
                name={name}
                value={value}
                checked={checked}
                onChange={ (event) => onChange(event, value) }
                disabled={disabled}
                className="form-check-input"
            />
            <label htmlFor={id} className="form-check-label">{label}</label>
        </div>
    );
};


const TextInput = (props) => {
    const { id, name, initial, classes, errors } = props;
    const [value, setValue] = useState(initial || "");
    const [_errors, setErrors] = useState(errors);

    return (
        <>
            <ErrorList errors={_errors} />
            <input
                type="text"
                name={name}
                id={id}
                onChange={ (event) => {
                    setValue(event.text);
                    setErrors([]);
                }}
                defaultValue={value}
                className={classes}
            ></input>
        </>
    );
};


export { CheckboxInput, CheckBoxInputBS, RadioInput, TextInput };
