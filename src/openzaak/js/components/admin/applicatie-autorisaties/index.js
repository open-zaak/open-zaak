import React from "react";
import ReactDOM from "react-dom";

import { AutorisatieFormSet } from './autorisatie-formset';

const Component = props => {
    return (
        <div>
            <AutorisatieFormSet extra={3} />
        </div>
    )
}


const mount = () => {
    const node = document.getElementById('react-autorisaties');
    if (!node) return;
    ReactDOM.render(<Component />, node);
}


mount();
