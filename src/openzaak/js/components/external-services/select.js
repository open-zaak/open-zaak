import React, { useContext, useState, useEffect } from 'react';


const SelectInput = (props) => {
    const { choices, name, initialValue, classes } = props;
    const [selected, setSelected] = useState(initialValue);
    // const [_errors, setErrors] = useState(errors);

    const options = choices.map(([value, label], index) => {
        return (
            <option key={index} value={value}>{label}</option>
        );
    });

    return (
        <select
            name={name}
            className={classes}
            value={selected}
            onChange={(event, value) => setSelected(value)}>
            { options }
        </select>
    );
};

export {SelectInput};
