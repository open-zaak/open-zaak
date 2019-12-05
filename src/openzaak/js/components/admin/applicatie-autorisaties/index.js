import React from "react";
import ReactDOM from "react-dom";

import { AutorisatieFormSet } from './autorisatie-formset';

const Component = props => {
    return (
        <div>

        </div>
    )
}


const mount = () => {
    const node = document.getElementById('react-autorisaties');
    if (!node) return;

    const scopeChoicesNode = document.getElementById('scope-choices');
    const scopeChoices = JSON.parse(scopeChoicesNode.text);

    ReactDOM.render(
        <AutorisatieFormSet
            extra={3}
            scopeChoices={scopeChoices}
        />,
        node
    );
}


mount();
