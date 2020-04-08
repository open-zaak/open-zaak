import React, { useState } from "react";
import PropTypes from "prop-types";


const AddRow = ({ className="add-row", onAdd, children }) => {
    return (
        <div className={className}>
            <a href="#" onClick={onAdd}>{ children }</a>
        </div>
    );
};

AddRow.propTypes = {
    className: PropTypes.string,
    onAdd: PropTypes.func.isRequired,
};

export { AddRow };
