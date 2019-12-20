import React from "react";
import PropTypes from "prop-types";

import { AutorisatieForm } from './autorisatie-form';


const ManagementForm = (props) => {
    const { prefix, initial_forms, total_forms, min_num_forms, max_num_forms } = props;
    return (
        <React.Fragment>
            <input type="hidden" name={`${prefix}-TOTAL_FORMS`} value={ total_forms } />
            <input type="hidden" name={`${prefix}-INITIAL_FORMS`} value={ initial_forms } />
            <input type="hidden" name={`${prefix}-MIN_NUM_FORMS`} value={ min_num_forms } />
            <input type="hidden" name={`${prefix}-MAX_NUM_FORMS`} value={ max_num_forms } />
        </React.Fragment>
    )
};


ManagementForm.propTypes = {
    prefix: PropTypes.string.isRequired,
    initial_forms: PropTypes.number.isRequired,
    total_forms: PropTypes.number.isRequired,
    min_num_forms: PropTypes.number.isRequired,
    max_num_forms: PropTypes.number.isRequired,
};


const AutorisatieFormSet = (props) => {
    const { config, formData } = props;

    // set up the existing forms
    const forms = formData.map(
        (data, index) => <AutorisatieForm key={index} index={index} data={data} />
    );

    // build the extra forms in the formset based on the extra parameter
    const numForms = forms.length;
    const extraForms = Array(config.extra).fill().map(
        (_, index) => <AutorisatieForm key={numForms + index} index={numForms + index} />
    );

    const allForms = forms.concat(extraForms);

    // render the entire component
    return (
        <React.Fragment>
            <ManagementForm
                prefix={config.prefix}
                initial_forms={config.INITIAL_FORMS}
                total_forms={config.TOTAL_FORMS}
                min_num_forms={config.MIN_NUM_FORMS}
                max_num_forms={config.MAX_NUM_FORMS}
            />
            <h2 className="autorisatie-formset__header">Autorisaties</h2>
            { allForms }
        </React.Fragment>
    );
};

AutorisatieFormSet.propTypes = {
    config: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        extra: PropTypes.number.isRequired,
        INITIAL_FORMS: PropTypes.number.isRequired,
        TOTAL_FORMS: PropTypes.number.isRequired,
        MIN_NUM_FORMS: PropTypes.number.isRequired,
        MAX_NUM_FORMS: PropTypes.number.isRequired,
    }).isRequired,
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export { AutorisatieFormSet };
