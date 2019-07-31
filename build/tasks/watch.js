'use strict';
var gulp = require('gulp');
var paths = require('../paths');
const { sass } = require('./sass');


/**
 * Watch-sass task
 * Run using "gulp watch-sass"
 * Runs "sass" task instantly and when any file in paths.sassSrc changes
 */
function watchSASS() {
    sass();
    gulp.watch(paths.sassSrc, sass);
}

exports.watchSASS = watchSASS;
gulp.task('watch-sass', watchSASS);

exports.watch = watchSASS;
gulp.task('watch', watchSASS);
