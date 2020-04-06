import React from "react";
import {ExternalForm} from "./external-form";


function ExternalFormSet(props) {
    const formData = props.formData;

    // set up the existing forms
    const forms = formData.map(
        (data, index) => <ExternalForm key={index} index={index} data={data} />
    );

    return (
        <div>
            <div className="form-group row text-center">
                <div className="col"><strong>Label</strong></div>
                <div className="col"><strong>API type</strong></div>
                <div className="col"><strong>Url</strong></div>
                <div className="col"><strong>NLX</strong></div>
                <div className="col"><strong>Authorization</strong></div>
            </div>

            {forms}
        </div>
    );

}

export { ExternalFormSet };
