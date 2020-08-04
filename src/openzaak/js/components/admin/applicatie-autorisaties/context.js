// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
import React from "react";

const ConstantsContext = React.createContext({
    scopeChoices: [],
    componentPrefixes: {},
    relatedTypeSelectionMethods: [],
    vertrouwelijkheidaanduidingChoices: [],
});

const CatalogiContext = React.createContext([]);

const PrefixContext = React.createContext('');

export { ConstantsContext, CatalogiContext, PrefixContext };
