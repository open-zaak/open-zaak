// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React, {useState} from "react";
import {ExternalForm} from "./external-form";
import {ManagementForm} from "../../../forms/management-form";
import PropTypes from "prop-types";

const AddRow = ({ className="add-row", onAdd, children }) => {
    return (
        <tr className={className}>
            <td colSpan="4">
                <a href="#" onClick={onAdd}>{ children }</a>
            </td>
        </tr>
    );
};

AddRow.propTypes = {
    className: PropTypes.string,
    onAdd: PropTypes.func.isRequired,
};


function ExternalFormSet(props) {
    const { config, formData } = props;
    const [ extra, setExtra ] = useState(config.TOTAL_FORMS - formData.length);

    // set up the existing forms
    const forms = formData.map(
        (data, index) => <ExternalForm key={index} index={index} data={data} />
    );

     // build the extra forms in the formset based on the extra parameter
    const numForms = forms.length;
    const extraForms = Array(extra).fill().map(
        (_, index) => <ExternalForm key={numForms + index} index={numForms + index} />
    );

    const allForms = forms.concat(extraForms);

    return (
        <div className="external-formset">
            <ManagementForm
                prefix={config.prefix}
                initial_forms={config.INITIAL_FORMS}
                total_forms={ formData.length + extra }
                min_num_forms={config.MIN_NUM_FORMS}
                max_num_forms={config.MAX_NUM_FORMS}
            />

            <fieldset className="module">
                <table className="table">
                    <caption>External services</caption>
                    <thead>
                        <tr>
                            <th className='external-form__hidden'></th>
                            <th className='external-formset__col'>Service</th>
                            <th className='external-formset__col'>API type</th>
                            <th className='external-formset__col--big'>URL</th>
                            <th className='external-formset__col'>NLX outway URL</th>
                            <th className='external-formset__col--big'>OAS URL</th>
                            <th className='external-formset__col'>Authorization</th>
                            <th className='external-formset__col--small'>Verwijderen</th>
                        </tr>
                    </thead>
                    <tbody>
                    { allForms }

                    <AddRow
                        className="external-formset__add-row"
                        onAdd={(event) => {
                            event.preventDefault();
                            setExtra(extra + 1);
                        }}>
                        Add Service
                    </AddRow>
                    </tbody>
                </table>
            </fieldset>

        </div>
    );

}

export { ExternalFormSet };
