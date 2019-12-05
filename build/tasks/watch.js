'use strict';
var gulp = require('gulp');
var paths = require('../paths');
const { sass } = require('./sass');
const { js } = require('./js');

/**
 * Watch-sass task
 * Run using "gulp watch-sass"
 * Runs "sass" task instantly and when any file in paths.sassSrc changes
 */
function watchSASS() {
    sass();
    gulp.watch(paths.sassSrc, sass);
}

/**
 * Watch-js task
 * Run using "gulp watch-js"
 * Runs "js" and "lint" tasks instantly and when any file in paths.jsSrc changes
 */
function watchJS() {
    js();
    gulp.watch([paths.jsSrc], js);
}

/**
 * Watch task
 * Run using "gulp watch"
 * Runs "watch-js" and "watch-sass" tasks
 */
const watch = gulp.parallel(watchJS, watchSASS);

exports.watchSASS = watchSASS;
gulp.task('watch-sass', watchSASS);

exports.watchJS = watchJS;
gulp.task('watch-js', watchJS);

exports.watch = watch;
gulp.task('watch', watch);
