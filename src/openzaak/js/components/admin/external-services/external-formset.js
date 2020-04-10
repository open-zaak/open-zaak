import React, {useState} from "react";
import {ExternalForm} from "./external-form";
import {ManagementForm} from "../../forms/management-form";
import {AddRow} from "../../forms/add-row";


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
        <>
            <ManagementForm
                prefix={config.prefix}
                initial_forms={config.INITIAL_FORMS}
                total_forms={ formData.length + extra }
                min_num_forms={config.MIN_NUM_FORMS}
                max_num_forms={config.MAX_NUM_FORMS}
            />

            <fieldset className="module">
                <table className="table">
                    <thead>
                        <tr>
                            <th className='external-form__hidden'></th>
                            <th>Label</th>
                            <th>API type</th>
                            <th>Url</th>
                            <th>NLX</th>
                            <th>Documentation</th>
                            <th>Authorization</th>
                        </tr>
                    </thead>
                    <tbody>
                    { allForms }
                    <AddRow
                        className="autorisatie-formset__add-row"
                        onAdd={(event) => {
                            event.preventDefault();
                            setExtra(extra + 1);
                        }}>
                        Add Service
                    </AddRow>
                    </tbody>
                </table>
            </fieldset>
        </>
    );

}

export { ExternalFormSet };
