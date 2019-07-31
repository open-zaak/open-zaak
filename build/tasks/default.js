const gulp = require('gulp');
const {watch} = require('./watch');

gulp.task('default', watch);
exports.default = watch;
