import React from "react";

const ConstantsContext = React.createContext({
    scopeChoices: [],
    componentPrefixes: {},
    relatedTypeSelectionMethods: [],
    vertrouwelijkheidaanduidingChoices: [],
});

export { ConstantsContext };
