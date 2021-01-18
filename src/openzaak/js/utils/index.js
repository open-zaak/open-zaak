// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
const jsonScriptToVar = (id) => {
    const node = document.getElementById(id);
    return JSON.parse(node.text);
};


export { jsonScriptToVar };
