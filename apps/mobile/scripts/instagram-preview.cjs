const path = require('node:path');

function previewCatalogPath({ appRoot, enabled, dev, platform }) {
  return enabled && dev === true && platform === 'ios'
    ? path.resolve(appRoot, '../../.local/instagram-probe/feed.v1.json')
    : path.join(appRoot, 'src/development/emptyInstagramCatalog.json');
}

function isLoopback(address) {
  return ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(address);
}

module.exports = { previewCatalogPath, isLoopback };
