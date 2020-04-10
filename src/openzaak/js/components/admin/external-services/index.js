import React from "react";
import ReactDOM from "react-dom";

import {ConstantsContext} from "./context";
import {ExternalFormSet} from "./external-formset";


const jsonScriptToVar = (id) => {
    const node = document.getElementById(id);
    return JSON.parse(node.text);
};


const mount = () => {
    const node = document.getElementById('react-external-services');
    if (!node) return;

    const authTypeChoices = jsonScriptToVar('auth-type-choices');
    const nlxOutway = jsonScriptToVar('nlx-outway');
    const nlxChoices = jsonScriptToVar('nlx-choices');

    const formsetConfig = jsonScriptToVar('formset-config');
    const formData = jsonScriptToVar('formdata');

    const constants = { authTypeChoices, nlxOutway, nlxChoices };

    ReactDOM.render(
        <ConstantsContext.Provider value={constants}>
            <ExternalFormSet config={formsetConfig} formData={formData}/>
        </ConstantsContext.Provider>,
        node
    );
};


mount();
