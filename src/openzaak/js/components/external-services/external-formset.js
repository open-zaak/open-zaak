import React from "react";
import {ExternalForm} from "./external-form";
import {ManagementForm} from "../../forms/management-form";


function ExternalFormSet(props) {
    const { config, formData } = props;

    // set up the existing forms
    const forms = formData.map(
        (data, index) => <ExternalForm key={index} index={index} data={data} />
    );

    return (
        <>
            <ManagementForm
                prefix={config.prefix}
                initial_forms={config.INITIAL_FORMS}
                total_forms={ formData.length }
                min_num_forms={config.MIN_NUM_FORMS}
                max_num_forms={config.MAX_NUM_FORMS}
            />

            <div className="form-group row text-center">
                <div className="col"><strong>Label</strong></div>
                <div className="col"><strong>API type</strong></div>
                <div className="col"><strong>Url</strong></div>
                <div className="col"><strong>NLX</strong></div>
                <div className="col"><strong>Authorization</strong></div>
            </div>

            {forms}
        </>
    );

}

export { ExternalFormSet };
