// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
import React, { useContext, useState, useEffect } from "react";
import PropTypes from "prop-types";

import { PrefixContext } from './context';
import { ErrorList } from '../../../forms/error-list';
import { RadioInput } from "../../../forms/inputs";
import { Choice, Err } from "../../../forms/types";


const RadioSelect = (props) => {
    const { choices, name, onChange, initialValue, errors } = props;

    const prefix = useContext(PrefixContext);
    const [currentValue, setCurrentValue] = useState(initialValue);
    const [_errors, setErrors] = useState(errors);

    const radios = choices.map( ([value, label], index) => {
        const _name = `${prefix}-${name}`;
        return (
            <li key={index} className="radio-select__radio">
                <RadioInput
                    name={_name}
                    value={value}
                    label={label}
                    i={index}
                    checked={value == currentValue}
                    onChange={ (event, value) => {
                        setCurrentValue(value);
                        setErrors([]);
                        if (onChange) {
                            onChange(value);
                        }
                    }}
                />
            </li>
        );
    });

    return (
        <React.Fragment>
            <ErrorList errors={_errors} />
            <ul className="radio-select">
                { radios }
            </ul>
        </React.Fragment>
    )
}

RadioSelect.propTypes = {
    choices: PropTypes.arrayOf(Choice),
    name: PropTypes.string.isRequired,
    initialValue: PropTypes.string,
    helpText: PropTypes.string,
    errors: PropTypes.arrayOf(Err),
    onChange: PropTypes.func,
};

RadioSelect.defaultProps = {
    initialValue: '',
    errors: [],
};

export { RadioSelect };
