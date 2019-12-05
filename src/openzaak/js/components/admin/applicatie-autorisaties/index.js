import React from "react";
import ReactDOM from "react-dom";


const Component = props => {
    return (
        <div> Admin React! </div>
    )
}


const mount = () => {
    const node = document.getElementById('react-autorisaties');
    if (!node) return;
    ReactDOM.render(<Component />, node);
}


mount();
