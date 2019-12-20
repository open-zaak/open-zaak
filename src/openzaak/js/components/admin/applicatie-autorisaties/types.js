import PropTypes from "prop-types";

const Choice = PropTypes.arrayOf(PropTypes.string);

const Err = PropTypes.shape({
    msg: PropTypes.string.isRequired,
    code: PropTypes.string,
});

export { Choice, Err };
