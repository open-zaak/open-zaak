import React from "react";
import ReactDOM from "react-dom";

import { AutorisatieFormSet } from './autorisatie-formset';

import { ConstantsContext } from './context';


const jsonScriptToVar = (id) => {
    const node = document.getElementById(id);
    return JSON.parse(node.text);
};


const mount = () => {
    const node = document.getElementById('react-autorisaties');
    if (!node) return;

    const scopeChoices = jsonScriptToVar('scope-choices');
    const componentPrefixes = jsonScriptToVar('component-scope-prefixes');
    const relatedTypeSelectionMethods = jsonScriptToVar('related-type-selection-methods');

    const constants = {scopeChoices, componentPrefixes, relatedTypeSelectionMethods};

    ReactDOM.render(
        <ConstantsContext.Provider value={constants}>
            <AutorisatieFormSet extra={3} />
        </ConstantsContext.Provider>,
        node
    );
}


mount();
