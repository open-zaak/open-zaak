const gulp = require('gulp');
const { sass } = require('./sass');

gulp.task('build', sass);
exports.build = sass;
