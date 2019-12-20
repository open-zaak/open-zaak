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


const TypeSelector = (props) => {
    const { typeInfo } = props;
    const [ verboseNamePlural, typeOptionsField ] = typeInfo;
    return (
        <React.Fragment>
            <h4 className="autorisatie-form__extra-title">Voor welke typen geldt dit?</h4>
            <TypesSelection verboseNamePlural={verboseNamePlural} typeOptionsField={typeOptionsField} />
        </React.Fragment>
    );
};

TypeSelector.propTypes = {
    typeInfo: PropTypes.array.isRequired,
};


const AutorisatieForm = (props) => {
    const { index, data } = props;
    const { values, errors } = data;

    const {scopeChoices, componentPrefixes } = useContext(ConstantsContext);
    const [selectedComponent, setSelectedComponent] = useState(values.component || '');
    const [availableScopeChoices, setAvailableScopeChoices] = useState(
        getAvailableScopeChoices(values.component, componentPrefixes, scopeChoices)
    );

    const showVA = VA_COMPONENTS.includes(selectedComponent);
    const showTypeSelection = COMPONENT_TO_TYPES[selectedComponent] != null;

    const isEven = (index % 2) === 0;

    return (
        <PrefixContext.Provider value={`form-${index}`}>

            <div className={`autorisatie-form autorisatie-form--${isEven ? 'even' : 'odd'}`}>
                <div className="autorisatie-form__component">
                    <h3 className="autorisatie-form__field-title">Component</h3>
                    <RadioSelect
                        choices={COMPONENT_CHOICES}
                        name="component"
                        initialValue={values.component}
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
                            <CheckboxSelect choices={availableScopeChoices} name="scopes" initialValue={values.scopes} /> :
                            <span className="autorisatie-form__select-component">(kies eerst een component)</span>
                    }
                </div>

                <div className="autorisatie-form__extra-container">
                    <h3 className="autorisatie-form__field-title">Extra parameters</h3>
                    <div className="autorisatie-form__extra">
                        {
                            (!showTypeSelection && !showVA) ?
                                <span className="autorisatie-form__select-component">(er zijn geen relevante extra opties)</span> :
                                null
                        }

                        {
                            // TODO: initialValue
                            showTypeSelection ?
                                (<div className="autorisatie-form__types-selection">
                                    <TypeSelector typeInfo={ COMPONENT_TO_TYPES[selectedComponent] } />
                                </div>) :
                                null
                        }

                        { showVA ?
                            (<div className="autorisatie-form__va-selection">
                                <VertrouwelijkheidAanduiding
                                    initialValue={values.vertrouwelijkheidaanduiding}
                                />
                            </div>) :
                            null
                        }

                    </div>
                </div>

            </div>

        </PrefixContext.Provider>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.shape({
        errors: PropTypes.object.isRequired,
        values: PropTypes.object.isRequired,
    }),
};

AutorisatieForm.defaultProps = {
    data: {errors: {}, values: {}}
};

export { AutorisatieForm };
