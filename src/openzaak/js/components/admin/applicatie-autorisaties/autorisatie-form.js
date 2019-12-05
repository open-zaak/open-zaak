import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { COMPONENT_CHOICES } from './constants';
import { CheckboxSelect } from './checkbox-select';
import { RadioSelect } from './radio-select';
import { Choice } from "./types";


const AutorisatieForm = (props) => {
    const { index, scopeChoices } = props;



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
