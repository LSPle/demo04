const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5000',  // 改为 5000
      changeOrigin: true,
      secure: false,
      ws: true,
      logLevel: 'silent'
    })
  );
};