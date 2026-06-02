const https = require('https');
const http = require('http');
const { URL } = require('url');

function fetch(urlStr) {
  return new Promise((resolve, reject) => {
    try {
      const url = new URL(urlStr);
      const mod = url.protocol === 'https:' ? https : http;
      const opts = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept-Charset': 'utf-8' },
        timeout: 10000,
      };
      mod.get(opts, res => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          return fetch(res.headers.location).then(resolve).catch(reject);
        }
        const chunks = [];
        res.on('data', c => { chunks.push(c); });
        res.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
      }).on('error', reject);
    } catch(e) { reject(e); }
  });
}

function extractTitles(html) {
  const titles = [];
  // Try title="..." attributes
  const re1 = /title=["']([^"']{8,120})["']/g;
  let m;
  while ((m = re1.exec(html)) !== null) {
    const t = m[1].trim();
    if (t && !titles.includes(t) && !t.match(/^(RSS|javascript|http|css|新浪|首页|登录|注册)/)) {
      titles.push(t);
    }
    if (titles.length >= 12) break;
  }
  // Try <a>text</a> patterns
  if (titles.length < 3) {
    const re2 = /<a[^>]{0,100}>([^<]{10,80})<\/a>/g;
    while ((m = re2.exec(html)) !== null) {
      const t = m[1].trim();
      if (t && !titles.includes(t) && t.match(/[\u4e00-\u9fff]/)) {
        titles.push(t);
      }
      if (titles.length >= 12) break;
    }
  }
  return titles;
}

async function main() {
  const sources = [
    { name: '新浪新闻', url: 'https://news.sina.com.cn/' },
    { name: 'IT之家', url: 'https://www.ithome.com/' },
    { name: '36氪', url: 'https://36kr.com/' },
    { name: '观察者网', url: 'https://www.guancha.cn/' },
  ];

  for (const s of sources) {
    try {
      const html = await fetch(s.url);
      const titles = extractTitles(html);
      console.log('### ' + s.name);
      titles.slice(0, 8).forEach((t, i) => console.log((i+1) + '. ' + t));
      if (titles.length === 0) console.log('(无法提取标题, 页面长度: ' + html.length + ')');
      console.log('');
    } catch (e) {
      console.log('### ' + s.name + ' - 错误: ' + e.message);
      console.log('');
    }
  }
}

main();
