import React, { useState, useContext } from "react";
import PropTypes from "prop-types";

import { COMPONENT_CHOICES } from './constants';
import { CheckboxSelect } from './checkbox-select';
import { RadioSelect } from './radio-select';
import { Choice } from "./types";

import { ConstantsContext, PrefixContext } from './context';

import { TypesSelection, VertrouwelijkheidAanduiding } from './extra-attributes';

const VA_COMPONENTS = [
    'zrc',
    'drc'
];

const COMPONENT_TO_TYPES = {
    // component: [verboseNamePlural, fieldOnSerializer]
    zrc: ['ZAAKTYPEN', 'zaaktypen'],
    drc: ['INFORMATIEOBJECTTYPEN', 'informatieobjecttypen'],
    brc: ['BESLUITTTYPEN', 'besluittypen'],
};

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

const getTypesSelection = (component) => {
    const typeInfo = COMPONENT_TO_TYPES[component];
    if (typeInfo == null) {
        return null;
    }

    const [ verboseNamePlural, typeOptionsField ] = typeInfo;
    return (
        <TypesSelection verboseNamePlural={verboseNamePlural} typeOptionsField={typeOptionsField} />
    );
};

const AutorisatieForm = (props) => {
    const { index } = props;

    const {scopeChoices, componentPrefixes } = useContext(ConstantsContext);
    const [selectedComponent, setSelectedComponent] = useState('');
    const [availableScopeChoices, setAvailableScopeChoices] = useState([]);

    const showVA = VA_COMPONENTS.includes(selectedComponent);

    return (
        <PrefixContext.Provider value={`form-${index}`}>

            <div className="autorisatie-form">
                <div className="autorisatie-form__component">
                    <RadioSelect
                        choices={COMPONENT_CHOICES}
                        name="component"
                        onChange={ (component) => {
                            setSelectedComponent(component);
                            const choices = getAvailableScopeChoices(component, componentPrefixes, scopeChoices);
                            setAvailableScopeChoices(choices);
                        }}
                    />
                </div>

                <div className="autorisatie-form__scopes">
                    <CheckboxSelect choices={availableScopeChoices} name="scopes" />
                </div>

                <div className="autorisatie-form__extra-attributes">
                    { getTypesSelection(selectedComponent) }
                </div>

                <div className="autorisatie-form__va">
                    { showVA ? <VertrouwelijkheidAanduiding /> : null }
                </div>

            </div>

        </PrefixContext.Provider>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
};

export { AutorisatieForm };
