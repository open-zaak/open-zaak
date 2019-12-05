import React, { useState, useContext } from "react";
import PropTypes from "prop-types";

import { COMPONENT_CHOICES } from './constants';
import { CheckboxSelect } from './checkbox-select';
import { RadioSelect } from './radio-select';
import { Choice } from "./types";

import { ScopeChoicesContext, ComponentPrefixContext } from './context';


const AutorisatieForm = (props) => {
    const { index } = props;

    const scopeChoices = useContext(ScopeChoicesContext);
    const componentPrefixes = useContext(ComponentPrefixContext);

    return (
        <div className="autorisatie-form">
            <div className="autorisatie-form__component">
                <RadioSelect
                    choices={COMPONENT_CHOICES}
                    prefix={`form-${index}`} name="component" />
            </div>

            <div className="autorisatie-form__scopes">
                <CheckboxSelect
                    choices={scopeChoices}
                    prefix={`form-${index}`} name="scopes" />
            </div>
        </div>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
    scopeChoices: PropTypes.arrayOf(Choice),
};

export { AutorisatieForm };
