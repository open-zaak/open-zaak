// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';
import useAsync from 'react-use/esm/useAsync';


const RESULTATEN_ENDPOINT = '/admin/api/v1/catalogi/selectielijst/resultaten';


const originalDismissRelatedLookupPopup = window.dismissRelatedLookupPopup;
const dismissRelatedLookupPopup = (win, chosenId) => {
    const result = originalDismissRelatedLookupPopup(win, chosenId);
    const name = win.name;
    const elem = document.getElementById(name);
    const event = new Event('change');
    elem.dispatchEvent(event);
    return result;
};


const SelectielijstklasseOptions = ({ zaaktypeId='' }) => {
    const {loading, error, value: options} = useAsync(
        async () => {
            if (!zaaktypeId) return [];
            const query = new URLSearchParams({zaaktype: zaaktypeId});
            const response = await window.fetch(`${RESULTATEN_ENDPOINT}?${query}`, {credentials: 'same-origin'});
            if (!response.ok) {
                throw new Error(response);
            }
            const choices = await response.json();
            return choices;
        },
        [zaaktypeId],
    );

    if (loading) {
        return 'Loading...';
    }

    if (error) {
        console.error(error);
        return `Error: ${error}`;
    }

    return (
        <>
            {
                options.map( ([value, label], index) => (
                    <li key={value}>
                        <label htmlFor={`selectielijst-scroll_${index}`}>
                            <input
                                type="radio"
                                name="selectielijstklasse"
                                value={value}
                                id={`selectielijst-scroll_${index}`}
                                defaultChecked={false}
                            />
                            &nbsp;{label}
                        </label>
                    </li>
                ) )
            }
        </>
    );
};

SelectielijstklasseOptions.propTypes = {
    zaaktypeId: PropTypes.string,
};



const renderSelectielijstklasseOptions = (root, zaaktypeId) => {
    ReactDOM.render(<SelectielijstklasseOptions zaaktypeId={zaaktypeId} />, root);
};


const init = () => {
    // check if we're actually on the right admin page
    const node = document.querySelector('body.app-catalogi.model-resultaattype.change-form');
    if (!node) return;

    // find the form fields
    const zaaktypeInput = document.querySelector('#resultaattype_form [name="zaaktype"]');
    const selectielijstScroll = document.getElementById('selectielijst-scroll');
    if (!zaaktypeInput || !selectielijstScroll) return;

    // monkeypatch because the change event doesn't fire...
    window.dismissRelatedLookupPopup = dismissRelatedLookupPopup;

    // bind change event to the zaaktype input
    zaaktypeInput.addEventListener('change', (event) => {
        const { value: zaaktypeId } = event.target;
        renderSelectielijstklasseOptions(selectielijstScroll, zaaktypeId);
    });
};


document.addEventListener('DOMContentLoaded', init);
