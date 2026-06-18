/**
 * OpenClaw 数据代理 — Node.js端
 * Python无法直连东方财富API，通过本代理中转
 * 运行：node proxy.js  (端口 9999)
 */
const http = require('http');
const https = require('https');
const url = require('url');

const PORT = 9999;
const CACHE = new Map();
const CACHE_TTL = 10000; // 10秒缓存

function fetchEastMoney(targetUrl) {
  return new Promise((resolve, reject) => {
    const cached = CACHE.get(targetUrl);
    if (cached && Date.now() - cached.time < CACHE_TTL) {
      return resolve(cached.data);
    }
    const options = {
      headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/' },
      rejectUnauthorized: false,
      timeout: 8000,
    };
    https.get(targetUrl, options, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try {
          JSON.parse(d); // validate
          CACHE.set(targetUrl, { data: d, time: Date.now() });
          resolve(d);
        } catch(e) { reject(new Error('Invalid JSON')); }
      });
    }).on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const parsed = url.parse(req.url, true);
  const target = parsed.query.url;

  if (parsed.pathname === '/api/proxy' && target) {
    try {
      const data = await fetchEastMoney(decodeURIComponent(target));
      res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
      res.end(data);
    } catch(e) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
  } else if (parsed.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok' }));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

server.listen(PORT, () => {
  console.log(`OpenClaw data proxy running on http://localhost:${PORT}`);
});
