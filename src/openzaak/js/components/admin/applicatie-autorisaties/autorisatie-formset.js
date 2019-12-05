import React from "react";
import PropTypes from "prop-types";

import { AutorisatieForm } from './autorisatie-form';
import { Choice } from "./types";


const AutorisatieFormSet = (props) => {
    const { extra, scopeChoices } = props;

    // build the forms in the formset based on the extra parameter
    const forms = Array(extra).fill().map(
        (_, index) => <AutorisatieForm key={index} index={index} scopeChoices={scopeChoices} />
    );

    // render the entire component
    return (
        <React.Fragment> { forms } </React.Fragment>
    );
};

AutorisatieFormSet.propTypes = {
    extra: PropTypes.number.isRequired,
    scopeChoices: PropTypes.arrayOf(Choice),
};

export { AutorisatieFormSet };
