// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React from "react";
import PropTypes from "prop-types";

const ManagementForm = (props) => {
    const { prefix, initial_forms, total_forms, min_num_forms, max_num_forms } = props;
    return (
        <React.Fragment>
            <input type="hidden" name={`${prefix}-TOTAL_FORMS`} defaultValue={ total_forms } />
            <input type="hidden" name={`${prefix}-INITIAL_FORMS`} defaultValue={ initial_forms } />
            <input type="hidden" name={`${prefix}-MIN_NUM_FORMS`} defaultValue={ min_num_forms } />
            <input type="hidden" name={`${prefix}-MAX_NUM_FORMS`} defaultValue={ max_num_forms } />
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


export { ManagementForm };
