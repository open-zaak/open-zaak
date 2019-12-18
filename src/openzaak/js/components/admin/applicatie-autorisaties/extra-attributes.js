import React, { useState, useContext, Fragment } from "react";
import PropTypes from "prop-types";

import { ConstantsContext, CatalogiContext } from './context';
import { RadioSelect } from './radio-select';
import { CheckboxSelect } from './checkbox-select';


const CatalogusOptions = (props) => {
    const { typeOptionsField, typeOptions, display } = props;
    const choices = typeOptions.map(
        ({id, str}) => [id.toString(), str]
    );
    return (
        <div className="catalogus-options">
            <span className="catalogus-options__title">{ display }</span>
            <CheckboxSelect choices={choices} name={ typeOptionsField } />
        </div>
    );
};


CatalogusOptions.propTypes = {
    typeOptionsField: PropTypes.string.isRequired,
    typeOptions: PropTypes.arrayOf(PropTypes.object).isRequired,
    display: PropTypes.string.isRequired,
};


const TypeOptions = (props) => {
    const { typeOptionsField } = props;
    const catalogi = useContext(CatalogiContext);
    return (
        <Fragment>
            { catalogi.map(catalogus => (
                <CatalogusOptions
                    key={ catalogus.id }
                    typeOptionsField={ typeOptionsField }
                    typeOptions={ catalogus[typeOptionsField] }
                    display={ catalogus.str }
                />)
            ) }
        </Fragment>
    );
};

TypeOptions.propTypes = {
    typeOptionsField: PropTypes.string.isRequired,
};


const TypesSelection = (props) => {
    const { verboseNamePlural, typeOptionsField } = props;
    const { relatedTypeSelectionMethods } = useContext(ConstantsContext);
    const [ showTypeOptions, setShowTypeOptions ] = useState(false);

    const formattedChoices = relatedTypeSelectionMethods.map(([value, repr]) => {
        repr = repr.replace('{verbose_name_plural}', verboseNamePlural);
        return [value, repr];
    });

    return (
        <Fragment>
            <RadioSelect
                choices={formattedChoices}
                name="related_type_selection"
                onChange={(relatedTypeSelectioNMethod) => {
                    // only show the explicit type selection if manual selection is picked
                    setShowTypeOptions(relatedTypeSelectioNMethod === 'manual_select');
                }}
            />

            <div className="type-options">
                { showTypeOptions ? <TypeOptions typeOptionsField={typeOptionsField} /> : null }
            </div>

        </Fragment>

    );
};

TypesSelection.propTypes = {
    verboseNamePlural: PropTypes.string.isRequired,
    typeOptionsField: PropTypes.string.isRequired,
}


const VertrouwelijkheidAanduiding = () => {
    const { vertrouwelijkheidaanduidingChoices } = useContext(ConstantsContext);
    return (
        <RadioSelect choices={vertrouwelijkheidaanduidingChoices} name="vertrouwelijkheidaanduiding" />
    );
};


export { TypesSelection, VertrouwelijkheidAanduiding };
