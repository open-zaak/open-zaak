import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { RadioInput } from "./inputs";
import { Choice } from "./types";


const RadioSelect = (props) => {
    const { choices, prefix, name } = props;

    const [currentValue, setCurrentValue] = useState(null);

    const radios = choices.map( ([value, label], index) => {
        const _name = `${prefix}-${name}`;
        return (
            <li key={index}>
                <RadioInput
                    name={_name}
                    value={value}
                    label={label}
                    i={index}
                    checked={value == currentValue}
                    onChange={ (event, value) => setCurrentValue(value) }
                />
            </li>
        );
    });

    return (
        <ul>
            { radios }
        </ul>
    )
}

RadioSelect.propTypes = {
    choices: PropTypes.arrayOf(Choice),
    prefix: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    helpText: PropTypes.string,
};

export { RadioSelect };
