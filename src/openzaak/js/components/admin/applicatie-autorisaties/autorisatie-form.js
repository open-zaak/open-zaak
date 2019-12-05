import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { COMPONENT_CHOICES } from './constants';
import { RadioSelect } from './radio-select';


const AutorisatieForm = (props) => {
    const { index } = props;

    return (
        <div className="autorisatie-form">
            <div className="autorisatie-form__component">
                <RadioSelect
                    choices={COMPONENT_CHOICES}
                    prefix={`form-${index}`} name="component" />
            </div>

            <div className="autorisatie-form__scopes">
                TODO: scopes
            </div>
        </div>
    );
};

AutorisatieForm.propTypes = {
    index: PropTypes.number.isRequired,
};

export { AutorisatieForm };
