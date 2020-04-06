import React from "react";
import ReactDOM from "react-dom";

import {ConstantsContext} from "../../admin/applicatie-autorisaties/context";
import {ExternalFormSet} from "./external-formset";


const jsonScriptToVar = (id) => {
    const node = document.getElementById(id);
    return JSON.parse(node.text);
};


const mount = () => {
    const node = document.getElementById('react-external-services');
    if (!node) return;

    const formData = jsonScriptToVar('formdata');

    ReactDOM.render(
        <ExternalFormSet formData={formData} />,
        node
    );
};


mount();
