import React from "react";
import PropTypes from "prop-types";

import { AutorisatieForm } from './autorisatie-form';


const AutorisatieFormSet = (props) => {
    const { extra, formData } = props;

    // set up the existing forms
    const forms = formData.map(
        (data, index) => <AutorisatieForm key={index} index={index} data={data} />
    );

    // build the extra forms in the formset based on the extra parameter
    const numForms = forms.length;
    const extraForms = Array(extra).fill().map(
        (_, index) => <AutorisatieForm key={numForms + index} index={numForms + index} />
    );

    const allForms = forms.concat(extraForms);

    // render the entire component
    return (
        <React.Fragment>
            <h2 className="autorisatie-formset__header">Autorisaties</h2>
            { allForms }
        </React.Fragment>
    );
};

AutorisatieFormSet.propTypes = {
    extra: PropTypes.number.isRequired,
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export { AutorisatieFormSet };
