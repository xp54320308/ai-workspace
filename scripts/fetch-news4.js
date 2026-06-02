const https = require('https');
const { URL } = require('url');

function fetch(urlStr) {
  return new Promise((resolve, reject) => {
    try {
      const url = new URL(urlStr);
      const opts = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' },
        timeout: 10000,
      };
      https.get(opts, res => {
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

async function main() {
  // Try Ars Technica and Defense News
  const sources = [
    { name: 'Ars Technica', url: 'https://arstechnica.com/' },
    { name: 'Defense News', url: 'https://www.defensenews.com/' },
    { name: '环球网', url: 'https://world.huanqiu.com/' },
  ];

  for (const s of sources) {
    try {
      const html = await fetch(s.url);
      const items = [];
      // Extract from <h2> or <h3> with links
      const re = /<h[23][^>]*>[\s\S]*?<a[^>]*href=["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>[\s\S]*?<\/h[23]>/g;
      let m;
      while ((m = re.exec(html)) !== null) {
        const text = m[2].replace(/<[^>]+>/g, '').trim();
        if (text && text.length >= 10 && text.length <= 150) {
          items.push(text);
        }
        if (items.length >= 8) break;
      }
      // Also try headline JSON
      if (items.length < 3) {
        const jsonRe = /"headline"\s*:\s*"([^"]{10,150})"/g;
        while ((m = jsonRe.exec(html)) !== null) {
          if (!items.includes(m[1])) items.push(m[1]);
          if (items.length >= 8) break;
        }
      }
      console.log('### ' + s.name);
      items.slice(0, 8).forEach((t, i) => console.log((i+1) + '. ' + t));
      if (items.length === 0) console.log('(无法提取, 长度: ' + html.length + ')');
      console.log('');
    } catch (e) {
      console.log('### ' + s.name + ' - 错误: ' + e.message);
      console.log('');
    }
  }
}

main();
