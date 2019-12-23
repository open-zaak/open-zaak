import React, { useState, useContext, Fragment } from "react";
import PropTypes from "prop-types";

import { CheckboxSelect } from './checkbox-select';
import { ConstantsContext, CatalogiContext } from './context';
import { ErrorList } from './error-list';
import { RadioSelect } from './radio-select';
import { Err, Pk } from './types';


const CatalogusOptions = (props) => {
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


CatalogusOptions.propTypes = {
    typeOptionsField: PropTypes.string.isRequired,
    typeOptions: PropTypes.arrayOf(PropTypes.object).isRequired,
    display: PropTypes.string.isRequired,
    selectedValues: PropTypes.arrayOf(Pk),
    onChange: PropTypes.func,
};

CatalogusOptions.defaultProps = {
    selectedValues: [],
};


const TypeOptions = (props) => {
    const { typeOptionsField, selectedValues, onChange } = props;
    const catalogi = useContext(CatalogiContext);
    return (
        <Fragment>
            { catalogi.map(catalogus => (
                <CatalogusOptions
                    key={ catalogus.id }
                    typeOptionsField={ typeOptionsField }
                    typeOptions={ catalogus[typeOptionsField] }
                    display={ catalogus.str }
                    onChange={ onChange }
                    selectedValues={ selectedValues }
                />)
            ) }
        </Fragment>
    );
};

TypeOptions.propTypes = {
    typeOptionsField: PropTypes.string.isRequired,
    selectedValues: PropTypes.arrayOf(Pk),
    onChange: PropTypes.func,
};

TypeOptions.defaultProps = {
    selectedValues: [],
};


const TypesSelection = (props) => {
    const { verboseNamePlural, typeOptionsField, initialValue, selectedValues, errors } = props;
    const { relatedTypeSelectionMethods } = useContext(ConstantsContext);
    const [ showTypeOptions, setShowTypeOptions ] = useState(initialValue === 'manual_select');

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
                }}
            />

            <div className="type-options">
                {
                    showTypeOptions ?
                        <TypeOptions
                            typeOptionsField={typeOptionsField}
                            selectedValues={selectedValues || []}
                            onChange={() => setErrors([])}
                        /> : null
                }
            </div>

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
