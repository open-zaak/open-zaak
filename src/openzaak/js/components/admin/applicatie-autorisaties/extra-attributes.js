// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
import React, { useState, useContext, Fragment } from "react";
import PropTypes from "prop-types";

import { CheckboxSelect } from './checkbox-select';
import { ConstantsContext, CatalogiContext, PrefixContext } from './context';
import { ErrorList } from '../../../forms/error-list';
import { TextInput } from '../../../forms/inputs';
import { RadioSelect } from './radio-select';
import { Err, Pk } from '../../../forms/types';


const TypeOptions = (props) => {
    const { typeOptionsField, typeOptions, display, selectedValues, onChange } = props;
    const choices = typeOptions.map(
        ({id, str}) => [id.toString(), str]
    );
    return (
        <div className="catalogus-options">
            <span className="catalogus-options__title">{ display }</span>
            <CheckboxSelect
                choices={ choices }
                name={ typeOptionsField }
                initialValue={ selectedValues.map(val => val.toString()) }
                onChange={ onChange }
            />
        </div>
    );
};


const CatalogusOptions = (props) => {
    const { selectedValues, onChange } = props;
    const catalogi = useContext(CatalogiContext);
    const choices = catalogi.map(
        ({id, naam}) => [id.toString(), naam]
    );
    return (
        <div className="catalogus-options">
            <CheckboxSelect
                choices={ choices }
                name={"catalogi"}
                initialValue={ selectedValues.map(val => val.toString()) }
                onChange={ onChange }
            />
        </div>
    );
};


TypeOptions.propTypes = {
    typeOptionsField: PropTypes.string.isRequired,
    typeOptions: PropTypes.arrayOf(PropTypes.object).isRequired,
    display: PropTypes.string.isRequired,
    selectedValues: PropTypes.arrayOf(Pk),
    onChange: PropTypes.func,
};

TypeOptions.defaultProps = {
    selectedValues: [],
};


const CatalogusTypeOptions = (props) => {
    const { typeOptionsField, selectedValues, onChange } = props;
    const catalogi = useContext(CatalogiContext);
    return (
        <Fragment>
            { catalogi.map(catalogus => (
                <TypeOptions
                    key={ catalogus.id }
                    typeOptionsField={ typeOptionsField }
                    typeOptions={ catalogus[typeOptionsField] }
                    display={ catalogus.str }
                    onChange={ onChange }
                    selectedValues={ selectedValues }
                />)
            ) }
        </Fragment>
    )
};

CatalogusTypeOptions.propTypes = {
    typeOptionsField: PropTypes.string.isRequired,
    selectedValues: PropTypes.arrayOf(Pk),
    onChange: PropTypes.func,
};

CatalogusTypeOptions.defaultProps = {
    selectedValues: [],
};


const TypesSelection = (props) => {
    const {
        verboseNamePlural,
        typeOptionsField,
        initialValue,
        selectedCatalogi,
        selectedValues,
        errors,
    } = props;
    const { relatedTypeSelectionMethods } = useContext(ConstantsContext);
    const [ showTypeOptions, setShowTypeOptions ] = useState(initialValue === 'manual_select');
    const [ showCatalogusOptions, setShowCatalogusOptions ] = useState(initialValue === 'select_catalogus');

    const [ _errors, setErrors ] = useState(errors);

    const formattedChoices = relatedTypeSelectionMethods.map(([value, repr]) => {
        repr = repr.replace('{verbose_name_plural}', verboseNamePlural);
        return [value, repr];
    });

    return (
        <Fragment>
            <ErrorList errors={_errors} />
            <RadioSelect
                choices={formattedChoices}
                name="related_type_selection"
                initialValue={initialValue}
                onChange={(relatedTypeSelectioNMethod) => {
                    // only show the explicit type selection if manual selection is picked
                    setShowTypeOptions(relatedTypeSelectioNMethod === 'manual_select');
                    setShowCatalogusOptions(relatedTypeSelectioNMethod === 'select_catalogus');
                }}
            />

            {
                showTypeOptions ?
                <div className="type-options">
                    <CatalogusTypeOptions
                        typeOptionsField={typeOptionsField}
                        selectedValues={selectedValues || []}
                        onChange={() => setErrors([])}
                    />
                </div> : null
            }

            {
                showCatalogusOptions ?
                <div className="type-options">
                    <CatalogusOptions
                        selectedValues={selectedCatalogi || []}
                        onChange={() => setErrors([])}
                    />
                </div> : null
            }

        </Fragment>

    );
};

TypesSelection.propTypes = {
    verboseNamePlural: PropTypes.string.isRequired,
    typeOptionsField: PropTypes.string.isRequired,
    initialValue: PropTypes.string,
    selectedValues: PropTypes.arrayOf(Pk),
    errors: PropTypes.arrayOf(Err),
};

TypesSelection.defaultProps = {
    initialValue: '',
    selectedValues: [],
    errors: [],
};


const VertrouwelijkheidAanduiding = (props) => {
    const { vertrouwelijkheidaanduidingChoices } = useContext(ConstantsContext);
    return (
        <Fragment>
            <h4 className="autorisatie-form__extra-title">Tot en met welke vertrouwelijkheidaanduiding?</h4>
            <RadioSelect
                choices={vertrouwelijkheidaanduidingChoices}
                name="vertrouwelijkheidaanduiding"
                {...props}
            />
        </Fragment>
    );
};


export { TypesSelection, VertrouwelijkheidAanduiding };
