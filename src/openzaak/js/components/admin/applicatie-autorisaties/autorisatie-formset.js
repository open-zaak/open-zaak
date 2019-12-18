import React from "react";
import PropTypes from "prop-types";

import { AutorisatieForm } from './autorisatie-form';


const AutorisatieFormSet = (props) => {
    const { extra } = props;

    // build the forms in the formset based on the extra parameter
    const forms = Array(extra).fill().map(
        (_, index) => <AutorisatieForm key={index} index={index} />
    );

    // render the entire component
    return (
        <React.Fragment>
            <h2 className="autorisatie-formset__header">Autorisaties</h2>
            { forms }
        </React.Fragment>
    );
};

AutorisatieFormSet.propTypes = {
    extra: PropTypes.number.isRequired,
};

export { AutorisatieFormSet };
