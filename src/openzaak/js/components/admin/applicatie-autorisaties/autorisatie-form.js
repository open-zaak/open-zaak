import React, { useState, useContext } from "react";
import PropTypes from "prop-types";

import { COMPONENT_CHOICES } from './constants';
import { CheckboxSelect } from './checkbox-select';
import { RadioSelect } from './radio-select';
import { Choice } from "./types";

import { ConstantsContext } from './context';

import { TypesSelection } from './extra-attributes';


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

const COMPONENT_TO_TYPES = {
    zrc: 'zaaktypen',
    drc: 'informatieobjecttypen',
    brc: 'besluitttypen',
};

const getTypesSelection = (component, prefix) => {
    if (COMPONENT_TO_TYPES[component] == null) {
        return null;
    }
    return (
        <TypesSelection prefix={prefix} verboseNamePlural={COMPONENT_TO_TYPES[component]} />
    );
};


const AutorisatieForm = (props) => {
    const { index } = props;

    const {scopeChoices, componentPrefixes } = useContext(ConstantsContext);
    const [selectedComponent, setSelectedComponent] = useState('');
    const [availableScopeChoices, setAvailableScopeChoices] = useState([]);

    return (
        <div className="autorisatie-form">
            <div className="autorisatie-form__component">
                <RadioSelect
                    choices={COMPONENT_CHOICES}
                    prefix={`form-${index}`}
                    name="component"
                    onChange={ (component) => {
                        setSelectedComponent(component);
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

            <div className="autorisatie-form__extra-attributes">
                { getTypesSelection(selectedComponent, `form-${index}`) }
            </div>

        </div>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
};

export { AutorisatieForm };
