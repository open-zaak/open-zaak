// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2019 - 2020 Dimpact
import React from "react";
import { createRoot } from "react-dom/client";

import { jsonScriptToVar } from '../../../utils';
import { AutorisatieFormSet } from './autorisatie-formset';
import { ConstantsContext, CatalogiContext } from './context';
import { Catalogus } from './data/catalogus';


const mount = () => {
    const node = document.getElementById('react-autorisaties');
    if (!node) return;

    const scopeChoices = jsonScriptToVar('scope-choices');
    const componentPrefixes = jsonScriptToVar('component-scope-prefixes');
    const relatedTypeSelectionMethods = jsonScriptToVar('related-type-selection-methods');
    const vertrouwelijkheidaanduidingChoices = jsonScriptToVar('vertrouwelijkheidaanduiding-choices');
    const catalogi = jsonScriptToVar('catalogi')
        .map(catalogus => new Catalogus(catalogus));

    const formsetConfig = jsonScriptToVar('formset-config');
    const formData = jsonScriptToVar('formdata');

    const constants = {
        scopeChoices,
        componentPrefixes,
        relatedTypeSelectionMethods,
        vertrouwelijkheidaanduidingChoices
    };

    if (!node._reactRoot) {
        node._reactRoot = createRoot(node);
    }
    node._reactRoot.render(
        <ConstantsContext.Provider value={constants}>
            <CatalogiContext.Provider value={catalogi}>
                <AutorisatieFormSet config={formsetConfig} formData={formData} />
            </CatalogiContext.Provider>
        </ConstantsContext.Provider>,
    );
}


mount();
