// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
import React, { useContext, useState, useEffect } from 'react';
import PropTypes from 'prop-types';

import { PrefixContext } from './context';
import { ErrorList } from '../../../forms/error-list';
import { CheckboxInput } from '../../../forms/inputs';
import { Choice, Err } from '../../../forms/types';


const getSelected = (selected, value, shouldInclude) => {
    if (!selected.includes(value) && shouldInclude) {
        selected.push(value);
    } else if (selected.includes(value) && !shouldInclude) {
        selected = selected.filter(x => x != value);
    }
    return selected;
};


const CheckboxSelect = (props) => {
    const { choices, name, helpText, initialValue, errors, onChange } = props;

    const prefix = useContext(PrefixContext);
    const [{selected}, setSelected] = useState({selected: initialValue});
    const [_errors, setErrors] = useState(errors);

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
                        setErrors([]);
                        if (onChange) {
                            onChange(newValue);
                        }
                    }}
                />
            </li>
        );
    });

    return (
        <React.Fragment>
            <ErrorList errors={_errors} />
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
    errors: PropTypes.arrayOf(Err),
    onChange: PropTypes.func,
};

CheckboxSelect.defaultProps = {
    initialValue: [],
    errors: [],
};

export { CheckboxSelect };
