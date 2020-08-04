// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
import React, { useState } from "react";
import PropTypes from "prop-types";

import { AutorisatieForm } from './autorisatie-form';
import { ManagementForm} from "../../../forms/management-form";


const AddRow = ({ className="add-row", onAdd, children }) => {
    return (
        <div className={className}>
            <a href="#" onClick={onAdd}>{ children }</a>
        </div>
    );
};

AddRow.propTypes = {
    className: PropTypes.string,
    onAdd: PropTypes.func.isRequired,
};


const AutorisatieFormSet = (props) => {
    const { config, formData } = props;

    const [ extra, setExtra ] = useState(config.TOTAL_FORMS - formData.length);

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
            <ManagementForm
                prefix={config.prefix}
                initial_forms={config.INITIAL_FORMS}
                total_forms={ formData.length + extra }
                min_num_forms={config.MIN_NUM_FORMS}
                max_num_forms={config.MAX_NUM_FORMS}
            />
            <h2 className="autorisatie-formset__header">Autorisaties</h2>

            { allForms }

            <AddRow
                className="autorisatie-formset__add-row"
                onAdd={(event) => {
                    event.preventDefault();
                    setExtra(extra + 1);
                }}>
                Nog Autorisaties toevoegen
            </AddRow>
        </React.Fragment>
    );
};

AutorisatieFormSet.propTypes = {
    config: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        INITIAL_FORMS: PropTypes.number.isRequired,
        TOTAL_FORMS: PropTypes.number.isRequired,
        MIN_NUM_FORMS: PropTypes.number.isRequired,
        MAX_NUM_FORMS: PropTypes.number.isRequired,
    }).isRequired,
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export { AutorisatieFormSet };
