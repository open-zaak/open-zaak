import React from "react";

const ConstantsContext = React.createContext({
    scopeChoices: [],
    componentPrefixes: {},
    relatedTypeSelectionMethods: [],
    vertrouwelijkheidaanduidingChoices: [],
});

const CatalogiContext = React.createContext([]);

export { ConstantsContext, CatalogiContext };
