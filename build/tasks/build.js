const gulp = require('gulp');
const { sass } = require('./sass');
const { js } = require('./js');

const build = gulp.parallel(sass, js);

gulp.task('build', build);
exports.build = build;
