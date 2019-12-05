import React from "react";
import ReactDOM from "react-dom";

import { AutorisatieFormSet } from './autorisatie-formset';

import { ScopeChoicesContext, ComponentPrefixContext } from './context';


const mount = () => {
    const node = document.getElementById('react-autorisaties');
    if (!node) return;

    const scopeChoicesNode = document.getElementById('scope-choices');
    const scopeChoices = JSON.parse(scopeChoicesNode.text);

    const componentPrefixesNode = document.getElementById('component-scope-prefixes');
    const componentPrefixes = JSON.parse(componentPrefixesNode.text);

    ReactDOM.render(
        <ScopeChoicesContext.Provider value={scopeChoices}>

            <ComponentPrefixContext.Provider value={componentPrefixes}>

                <AutorisatieFormSet extra={3} />

            </ComponentPrefixContext.Provider>

        </ScopeChoicesContext.Provider>,
        node
    );
}


mount();
