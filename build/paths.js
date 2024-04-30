const fs = require('fs');


/** Parses package.json */
const pkg = JSON.parse(fs.readFileSync('./package.json', 'utf-8'));

/** Name of the sources directory */
const sourcesRoot = `src/${pkg.name}/`;

/** Name of the static (source) directory */
const staticRoot = `${sourcesRoot}static/`;


/**
 * Application path configuration for use in frontend scripts
 */
module.exports = {
    // Parsed package.json
    package: pkg,

     // Path to the scss entry point
    sassEntry: `${sourcesRoot}sass/screen.scss`,

    // Path to the sass (sources) directory
    sassSrcDir: `${sourcesRoot}sass/`,

    // Path to the sass (sources) entry point
    sassSrc: `${sourcesRoot}sass/**/*.scss`,

    jsSrc: `${sourcesRoot}js/**/*.js`,

    jsDir: `${staticRoot}bundles/`,

    // Path to the js entry point (source)
    jsEntry: `${sourcesRoot}js/index.js`,
};
