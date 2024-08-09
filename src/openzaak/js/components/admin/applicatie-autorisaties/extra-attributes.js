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

const AddExternalType = (props) => {
    const { onAdd } = props;
    return (
        <div>
            <button className="catalogus-options__add-type add-array-item" type="button" onClick={onAdd}>Add another</button>
        </div>
    );
};

AddExternalType.propTypes = {
    onAdd: PropTypes.func.isRequired,
};

const ExternalType = (props) => {
    const { index, initial, errors } = props;
    const prefix = useContext(PrefixContext);
    const id = `id_${prefix}-externe_typen_${index}`;
    const name = `${prefix}-externe_typen`;
    return (
        <li className="catalogus-options__external-type array-item">
            <TextInput
                id={id}
                name={name}
                initial={initial}
            />
        </li>
    );
};

const ExternalTypes = (props) => {
    const { externalValues, typeOptionsField, errors } = props;
    const [ extra, setExtra ] = useState((externalValues.length > 0) ? externalValues.length - 1 : 0);

    const types = Array(1).fill().map(
        (_, index) => <ExternalType
                        key={index}
                        index={index}
                        initial={externalValues[index]}
                      />
    );
    const numTypes = types.length;
    const extraTypes = Array(extra).fill().map(
        (_, index) => <ExternalType
                        key={numTypes+index}
                        index={numTypes+index}
                        initial={externalValues[numTypes+index]}
                      />
    );

    const allTypes = types.concat(extraTypes)

    return (
        <Fragment>
            <ErrorList errors={errors} />

            <div className="catalogus-options dynamic-array-widget">
                <h5>Externe {typeOptionsField}</h5>

                <ul className="catalogus-options__external-types">{ allTypes }</ul>
                <AddExternalType
                    onAdd={(event) => {
                        event.preventDefault();
                        setExtra(extra + 1);
                    }}>
                    Nog een extern type toevoegen
                </AddExternalType>
            </div>
        </Fragment>
    );
};


const CatalogusTypeOptions = (props) => {
    const { typeOptionsField, selectedValues, externalValues, onChange, errorsExternal } = props;
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
            <ExternalTypes externalValues={externalValues} errors={errorsExternal} typeOptionsField={typeOptionsField} />
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
        externalValues,
        errors,
        errorsExternal
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
                        externalValues={externalValues || []}
                        errorsExternal={errorsExternal || []}
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
