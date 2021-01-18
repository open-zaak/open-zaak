// SPDX-License-Identifier: EUPL-1.2
// Copyright (C) 2020 Dimpact
import PropTypes from "prop-types";

const Choice = PropTypes.arrayOf(PropTypes.string);

const Err = PropTypes.shape({
    msg: PropTypes.string.isRequired,
    code: PropTypes.string,
});

const Pk = PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
]);

export { Choice, Err, Pk };
