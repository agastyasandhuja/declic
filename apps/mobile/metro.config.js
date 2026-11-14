const path = require('node:path');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
// These shared inputs are outside npm workspace packages, so watch them too.
config.watchFolders = [...new Set([
  ...config.watchFolders,
  path.resolve(__dirname, '../../contracts'),
  path.resolve(__dirname, '../../fixtures'),
])];
module.exports = config;
