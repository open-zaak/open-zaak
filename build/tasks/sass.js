'use strict';
var gulp = require('gulp');
var gulpif = require('gulp-if');
var postcss = require('gulp-postcss');
var sourcemaps = require('gulp-sourcemaps');
var sass = require('gulp-sass');
var autoprefixer = require('autoprefixer');
var cssnano = require('cssnano');
var selectorLint = require('postcss-selector-lint');
var argv = require('yargs').argv;
var paths = require('../paths');


var isProduction = argv.production ? true : false;
var sourcemap = argv.sourcemap ? true : false;


let selectorLintConfig = {
    global: {
        // Simple
        type: true,
        class: true,
        id: false,
        universal: false,
        attribute: false,

        // Pseudo
        psuedo: false,
    },

    local: {
        // Simple
        type: true,
        class: true,
        id: false,
        universal: true,
        attribute: true,

        // Pseudo
        psuedo: true,
    },

    options: {
        excludedFiles: ['admin_overrides.css'],
    }
};


var plugins = isProduction
              ? [cssnano(), autoprefixer()]
              : [autoprefixer(), selectorLint(selectorLintConfig)];


/**
 * sass task
 * Run using "gulp sass"
 * Searches for sass files in paths.sassSrc
 * Compiles sass to css
 * Auto prefixes css
 * Optimizes css when used with --production
 * Writes css to paths.cssDir
 */
function scss() {
    return gulp.src(paths.sassSrc)
        .pipe(gulpif(sourcemap, sourcemaps.init()))
        .pipe(sass({
            outputStyle: isProduction ? 'compressed' : 'expanded',
            includePaths: 'node_modules/',
        }).on('error', sass.logError))
        .pipe(postcss(plugins))
        .pipe(gulpif(sourcemap, sourcemaps.write('./')))
        .pipe(gulp.dest(paths.cssDir));
}


gulp.task('sass', scss);
exports.sass = scss;
