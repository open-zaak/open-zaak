import React, { useState, useContext } from "react";
import PropTypes from "prop-types";

import { COMPONENT_CHOICES } from './constants';
import { CheckboxSelect } from './checkbox-select';
import { RadioSelect } from './radio-select';
import { Choice } from "./types";

import { ScopeChoicesContext, ComponentPrefixContext } from './context';


const matchesPrefix = (scope, prefixes) => {
    const matchPrefixes = prefixes.filter(prefix => scope.startsWith(`${prefix}.`));
    return matchPrefixes.length > 0;
};


const getAvailableScopeChoices = (component, componentPrefixes, scopeChoices) => {
    const prefixes = componentPrefixes[component] || [];
    const choices = scopeChoices.filter(
        ([scope, label]) => matchesPrefix(scope, prefixes)
    );
    return choices;
};


const AutorisatieForm = (props) => {
    const { index } = props;

    const scopeChoices = useContext(ScopeChoicesContext);
    const componentPrefixes = useContext(ComponentPrefixContext);

    const [availableScopeChoices, setAvailableScopeChoices] = useState([]);

    return (
        <div className="autorisatie-form">
            <div className="autorisatie-form__component">
                <RadioSelect
                    choices={COMPONENT_CHOICES}
                    prefix={`form-${index}`} name="component"
                    onChange={ (component) => {
                        const choices = getAvailableScopeChoices(component, componentPrefixes, scopeChoices);
                        setAvailableScopeChoices(choices);
                    }}
                />
            </div>

            <div className="autorisatie-form__scopes">
                <CheckboxSelect
                    choices={availableScopeChoices}
                    prefix={`form-${index}`} name="scopes"
                />
            </div>
        </div>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
};

export { AutorisatieForm };
