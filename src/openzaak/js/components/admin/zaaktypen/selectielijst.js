// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';
import useAsync from 'react-use/esm/useAsync';

const PROCESTYPEN_ENDPOINT = '/admin/api/v1/catalogi/selectielijst/procestypen';


const ProcestypeOptions = ({ year, initialValue='' }) => {
    const {loading, error, value: procestypen=[]} = useAsync(
        async () => {
            const query = new URLSearchParams({ year });
            const response = await window.fetch(`${PROCESTYPEN_ENDPOINT}?${query}`, {credentials: 'same-origin'});
            if (!response.ok) {
                throw new Error(response);
            }
            const choices = await response.json();
            return choices;
        },
        [year],
    );

    if (error) {
        console.error(error);
        return `Error: ${error}`;
    }

    // ensure that the select re-renders when the year changes AND the resulting procestypen
    // state is updated. If you don't do this, then the props of the select never change
    // and the `defaultValue` appears to not be working.
    const selectKey = `${year}-${procestypen.length ? procestypen[0].url : ''}`;

    return (
        <>
            <label htmlFor="id_selectielijst_procestype">Selectielijst procestype:</label>
            <select key={selectKey} defaultValue={initialValue} name="selectielijst_procestype" id="id_selectielijst_procestype">
                {
                    loading
                    ? <option value="">Loading...</option>
                    : procestypen.map(procestype => (
                        <option key={procestype.url} value={procestype.url} >
                            {`${procestype.nummer} - ${procestype.naam}`}
                        </option>
                    ))
                }
            </select>
            <div className="help">
                URL-referentie naar een vanuit archiveringsoptiek onderkende groep processen met dezelfde kenmerken (PROCESTYPE in de Selectielijst API).
            </div>
        </>
    );
};

ProcestypeOptions.propTypes = {
    year: PropTypes.number.isRequired,
    initialValue: PropTypes.string,
};


const renderProcestypeOptions = (root, initialValue, year) => {
    ReactDOM.render(
        <React.StrictMode>
            <ProcestypeOptions initialValue={initialValue} year={year} />
        </React.StrictMode>,
        root
    );
};


const init = () => {
    // check if we're actually on the right admin page
    const node = document.querySelector('body.app-catalogi.model-zaaktype.change-form');
    if (!node) return;

    // find the form fields
    const selectielijstJaarField = document.querySelector('#zaaktype_form [name="selectielijst_procestype_jaar"]');
    const selectielijstProcestypeField = document.querySelector('#zaaktype_form [name="selectielijst_procestype"]');
    if (!selectielijstJaarField || !selectielijstProcestypeField) return;

    // copy some of the DOM around to replace it seemlessy
    const selectedProcestype = selectielijstProcestypeField.value.toString();
    const container = selectielijstProcestypeField.parentNode; // this is the container div

    // bind change event to the year form field
    selectielijstJaarField.addEventListener('change', (event) => {
        const year = parseInt(event.target.value, 10);
        renderProcestypeOptions(container, selectedProcestype, year);
    });
};


document.addEventListener('DOMContentLoaded', init);
