import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { CheckboxInput } from "./inputs";
import { Choice } from "./types";


const CheckboxSelect = (props) => {
    const { choices, prefix, name } = props;

    const [currentValue, setCurrentValue] = useState([]);

    const Checkboxs = choices.map( ([value, label], index) => {
        const _name = `${prefix}-${name}`;
        return (
            <li key={index}>
                <CheckboxInput
                    name={_name}
                    value={value}
                    label={label}
                    i={index}
                    checked={value == currentValue}
                    onChange={setCurrentValue}
                />
            </li>
        );
    });

    return (
        <ul>
            { Checkboxs }
        </ul>
    )
}

CheckboxSelect.propTypes = {
    choices: PropTypes.arrayOf(Choice),
    prefix: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    helpText: PropTypes.string,
};

export { CheckboxSelect };
