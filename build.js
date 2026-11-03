/**
 * Minimal build script for simple JS and SCSS.
 *
 * For simple projects, this should suffice. If you have more advanced needs, consider
 * using a more flexible build system, e.g. ViteJS.
 *
 * Note that this simplified setup does not support watch mode, but using esbuild should
 * be plenty fast to get by.
 */
import * as esbuild from 'esbuild';
import { sassPlugin } from 'esbuild-sass-plugin';
import * as sass from "sass-embedded";

// Check if the `--watch` flag is passed in the command line
const args = process.argv.slice(2);
const isWatchMode = args.includes('--watch');

let params = {
    entryPoints: {
        screen: 'src/openzaak/sass/screen.scss',
        admin_overrides: 'src/openzaak/sass/admin/admin_overrides.scss',
        index: 'src/openzaak/js/index.js',
    },
    bundle: true,
    minify: true,
    sourcemap: true,
    loader: { '.js': 'jsx' },
    jsx: 'automatic', // <-- Use the new JSX transform
    jsxImportSource: 'react', // <-- Required for the new transform
    outdir: 'src/openzaak/static/bundles/',
    plugins: [sassPlugin({
        embedded: true,
        importers: [new sass.NodePackageImporter()],
    })],
    external: ['*.svg', '*.png', '*.woff2', '*.ttf'],
}

if (isWatchMode) {
    let ctx = await esbuild.context(params)
    await ctx.watch()
} else {
    await esbuild.build(params)
}