const path = require('node:path');
const { getDefaultConfig } = require('expo/metro-config');
const { previewCatalogPath, isLoopback } = require('./scripts/instagram-preview.cjs');

const config = getDefaultConfig(__dirname);
const privatePreview = process.env.HACKUMASS_INSTAGRAM_PREVIEW === '1';
const exporting = process.argv.includes('export');
if (privatePreview && !exporting && !process.argv.includes('--localhost')) {
  throw new Error('The private Instagram preview requires --localhost. Use npm run ios:instagram.');
}
// These shared inputs are outside npm workspace packages, so watch them too.
config.watchFolders = [...new Set([
  ...config.watchFolders,
  path.resolve(__dirname, '../../contracts'),
  path.resolve(__dirname, '../../fixtures'),
  ...(privatePreview && !exporting ? [path.resolve(__dirname, '../../.local/instagram-probe')] : []),
])];
const originalResolver = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName === '@local/instagram-preview') {
    const filePath = previewCatalogPath({ appRoot: __dirname, enabled: privatePreview && !exporting, dev: context.dev, platform });
    return context.resolveRequest(context, filePath, platform);
  }
  return originalResolver ? originalResolver(context, moduleName, platform) : context.resolveRequest(context, moduleName, platform);
};
if (privatePreview && !exporting) {
  const enhance = config.server.enhanceMiddleware;
  config.server.enhanceMiddleware = (middleware, server) => {
    const handler = enhance ? enhance(middleware, server) : middleware;
    return (request, response, next) => {
      if (!isLoopback(request.socket.remoteAddress)) { response.writeHead(403); response.end('Local simulator preview only.'); return; }
      handler(request, response, next);
    };
  };
}
module.exports = config;
