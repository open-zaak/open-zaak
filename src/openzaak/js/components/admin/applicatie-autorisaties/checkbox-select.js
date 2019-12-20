import React, { useContext, useState, useEffect } from "react";
import PropTypes from "prop-types";

import { PrefixContext } from './context';
import { CheckboxInput } from "./inputs";
import { Choice } from "./types";


const getSelected = (selected, value, shouldInclude) => {
    if (!selected.includes(value) && shouldInclude) {
        selected.push(value);
    } else if (selected.includes(value) && !shouldInclude) {
        selected = selected.filter(x => x != value);
    }
    return selected;
};


const CheckboxSelect = (props) => {
    const { choices, name, helpText, initialValue } = props;
    const prefix = useContext(PrefixContext);
    const [{selected}, setSelected] = useState({selected: initialValue});

    const checkboxes = choices.map( ([value, label], index) => {
        const _name = `${prefix}-${name}`;
        return (
            <li key={index} className="checkbox-select__checkbox">
                <CheckboxInput
                    name={_name}
                    value={value}
                    label={label}
                    i={index}
                    checked={selected.includes(value)}
                    onChange={(event, value) => {
                        const shouldInclude = event.target.checked;
                        const newValue = getSelected(selected, value, shouldInclude);
                        setSelected({selected: newValue});
                    }}
                />
            </li>
        );
    });

    return (
        <React.Fragment>
            <ul className="checkbox-select">
                { checkboxes }
            </ul>
            { helpText ? <p class="help-text"> {helpText} </p> : null }
        </React.Fragment>
    )
}

CheckboxSelect.propTypes = {
    choices: PropTypes.arrayOf(Choice),
    name: PropTypes.string.isRequired,
    initialValue: PropTypes.arrayOf(PropTypes.string),
    helpText: PropTypes.string,
};

CheckboxSelect.defaultProps = {
    initialValue: [],
};

export { CheckboxSelect };
