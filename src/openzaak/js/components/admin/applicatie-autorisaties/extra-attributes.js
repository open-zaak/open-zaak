import React, { useState, useContext } from "react";
import PropTypes from "prop-types";

import { ConstantsContext } from './context';
import { RadioSelect } from './radio-select';


const TypesSelection = (props) => {
    const { prefix, verboseNamePlural } = props;
    const { relatedTypeSelectionMethods } = useContext(ConstantsContext);

    const formattedChoices = relatedTypeSelectionMethods.map(([value, repr]) => {
        repr = repr.replace('{verbose_name_plural}', verboseNamePlural);
        return [value, repr];
    });

    return (
        <RadioSelect
            choices={formattedChoices}
            prefix={prefix}
            name="related_type_selection"
            onChange={(relatedTypeSelectioNMethod) => {
                console.log(relatedTypeSelectioNMethod);
            }}
        />
    );
};

TypesSelection.propTypes = {
    prefix: PropTypes.string.isRequired,
    verboseNamePlural: PropTypes.string.isRequired,
    onChange: PropTypes.func,
}


export { TypesSelection };
