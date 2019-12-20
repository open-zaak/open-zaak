import React, { useContext, useState, useEffect } from "react";
import PropTypes from "prop-types";

import { PrefixContext } from './context';
import { RadioInput } from "./inputs";
import { Choice } from "./types";


const RadioSelect = (props) => {
    const { choices, name, onChange, initialValue } = props;
    const prefix = useContext(PrefixContext);
    const [currentValue, setCurrentValue] = useState(initialValue);

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
                        if (onChange) {
                            onChange(value);
                        }
                    }}
                />
            </li>
        );
    });

    return (
        <ul className="radio-select">
            { radios }
        </ul>
    )
}

RadioSelect.propTypes = {
    choices: PropTypes.arrayOf(Choice),
    name: PropTypes.string.isRequired,
    initialValue: PropTypes.string,
    helpText: PropTypes.string,
    onChange: PropTypes.func,
};

RadioSelect.defaultProps = {
    initialValue: '',
};

export { RadioSelect };
