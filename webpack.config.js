const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const argv = require('yargs').argv;
const paths = require('./build/paths');

// Set isProduction based on environment or argv.
let isProduction = process.env.NODE_ENV === 'production';
if (argv.production) {
    isProduction = true;
}

/**
 * Webpack configuration
 * Run using "webpack" or "npm run build"
 */
module.exports = {
    // Entry points locations
    entry: {
        [`${paths.package.name}-css`]: `${__dirname}/${paths.sassEntry}`,
        [`${paths.package.name}-js`]: `${__dirname}/${paths.jsEntry}`,
        'admin_overrides': `${__dirname}/${paths.sassSrcDir}/admin/admin_overrides.scss`,
    },

    // (Output) bundle locations.
    output: {
        path: __dirname + '/' + paths.jsDir, // directory
        filename: '[name].js', // file
        chunkFilename: '[name].bundle.js',
        publicPath: '/static/bundles/',
    },

     // Plugins
    plugins: [
        new MiniCssExtractPlugin(),
    ],

    // Add babel (see .babelrc for settings)
    module: {
        rules: [
            // .js
            {
                exclude: /node_modules/,
                loader: 'babel-loader',
                test: /.js?$/
            },
            // .js
          {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    // Writes css files.
                    MiniCssExtractPlugin.loader,

                    // Loads CSS files.
                    {
                        loader: 'css-loader',
                        options: {
                            url: false
                        },
                    },

                    // Runs postcss configuration (postcss.config.js).
                    {
                        loader: 'postcss-loader'
                    },

                    // Compiles .scss to .css.
                    {
                        loader: 'sass-loader',
                        options: {
                            sassOptions: {
                                comments: false,
                                style: 'compressed'
                            },
                            sourceMap: argv.sourcemap
                        },
                    },
                ],
            },
        ]
    },

    // Use --production to optimize output.
    mode: isProduction ? 'production' : 'development',

    // Use --sourcemap to generate sourcemap.
    devtool: argv.sourcemap ? 'sourcemap' : false,
};
