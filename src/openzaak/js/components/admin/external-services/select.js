// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React, { useContext, useState, useEffect } from 'react';
import {ErrorList} from "../../../forms/error-list";


const SelectInput = (props) => {
    const { choices, name, initialValue, classes, errors, onChange, id } = props;
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
                id={id}
                onChange={(event) => {
                    setSelected(event.target.value);
                    setErrors([]);
                    if (onChange) {
                        onChange(event.target.value);
                    }
                }}>
                { options }
            </select>
        </>
    );
};

export {SelectInput};
