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
    const formData = jsonScriptToVar('formdata');

    const constants = {authTypeChoices};

    ReactDOM.render(
        <ConstantsContext.Provider value={constants}>
            <ExternalFormSet formData={formData} />
        </ConstantsContext.Provider>,
        node
    );
};


mount();
