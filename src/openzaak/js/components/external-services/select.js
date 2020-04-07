import React, { useContext, useState, useEffect } from 'react';
import {ErrorList} from "../../forms/error-list";


const SelectInput = (props) => {
    const { choices, name, initialValue, classes, errors } = props;
    const [selected, setSelected] = useState(initialValue);
    const [_errors, setErrors] = useState(errors);

    const options = choices.map(([value, label], index) => {
        return (
            <option key={index} value={value}>{label}</option>
        );
    });

    return (
        <>
            <ErrorList errors={_errors} />

            <select
                name={name}
                className={classes}
                value={selected}
                onChange={(event, value) => {
                    setSelected(value);
                    setErrors([]);
                    if (onChange) {
                        onChange(value);
                    }
                }}>
                { options }
            </select>
        </>
    );
};

export {SelectInput};
