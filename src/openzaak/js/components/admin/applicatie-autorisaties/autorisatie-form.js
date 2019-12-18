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

    const isEven = (index % 2) === 0;

    return (
        <PrefixContext.Provider value={`form-${index}`}>

            <div className={`autorisatie-form autorisatie-form--${isEven ? 'even' : 'odd'}`}>
                <div className="autorisatie-form__component">
                    <h3 className="autorisatie-form__field-title">Component</h3>
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
                    <h3 className="autorisatie-form__field-title">Selecteer scopes</h3>
                    {
                        availableScopeChoices.length ?
                            <CheckboxSelect choices={availableScopeChoices} name="scopes" /> :
                            '(kies eerst een component)'
                    }
                </div>

                <div className="autorisatie-form__extra">
                    <h3 className="autorisatie-form__field-title">Extra parameters</h3>
                    <div className="autorisatie-form__types-selection">
                        { getTypesSelection(selectedComponent) }
                    </div>
                    <div className="autorisatie-form__va-selection">
                        { showVA ? <VertrouwelijkheidAanduiding /> : null }
                    </div>
                </div>

            </div>

        </PrefixContext.Provider>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
};

export { AutorisatieForm };
