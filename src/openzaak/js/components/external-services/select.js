import React, { useContext, useState, useEffect } from 'react';


const SelectInput = (props) => {
    const { choices, name, initialValue, classes } = props;
    const [selected, setSelected] = useState(initialValue);
    // const [_errors, setErrors] = useState(errors);

    const options = choices.map(([value, label], index) => {
        return (
            <option value={value} selected={value == selected}>{label}</option>
        );
    });

    return (
        <select
            name={name}
            className={classes}
            onChange={(event, value) => setSelected(value)}>
            { options }
        </select>
    );
};

export {SelectInput};
