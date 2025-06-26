// This file is used to configure the Netlify build process
// It copies the necessary files to the correct locations

const fs = require('fs-extra');
const path = require('path');

// Copy the static files to the publish directory
fs.copySync('web/static', 'dist');

// Copy the _redirects file to the publish directory
fs.copyFileSync('_redirects', 'dist/_redirects');

console.log('Files copied successfully!'); 