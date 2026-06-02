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

function extractH2H3(html) {
  const items = [];
  const re = /<h[23][^>]*>([\s\S]*?)<\/h[23]>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim();
    if (text && text.length >= 8 && text.length <= 120) {
      items.push(text);
    }
    if (items.length >= 10) break;
  }
  return items;
}

function extractFromJson(html) {
  const items = [];
  // Look for JSON-LD or structured data
  const jsonRe = /"headline"\s*:\s*"([^"]{10,120})"/g;
  let m;
  while ((m = jsonRe.exec(html)) !== null) {
    items.push(m[1]);
    if (items.length >= 10) break;
  }
  return items;
}

async function main() {
  const sources = [
    { name: '机器之心', url: 'https://www.jiqizhixin.com/' },
    { name: '量子位', url: 'https://www.qbitai.com/' },
    { name: '虎嗅', url: 'https://www.huxiu.com/' },
    { name: '少数派', url: 'https://sspai.com/' },
  ];

  for (const s of sources) {
    try {
      const html = await fetch(s.url);
      let items = extractFromJson(html);
      if (items.length < 3) {
        items = extractH2H3(html);
      }
      if (items.length < 3) {
        // Try <a>text</a> with Chinese
        const re = /<a[^>]{0,200}>([^<]{10,80})<\/a>/g;
        let m;
        while ((m = re.exec(html)) !== null) {
          const t = m[1].trim();
          if (t.match(/[\u4e00-\u9fff]/) && !items.includes(t) && t.length >= 10) {
            items.push(t);
          }
          if (items.length >= 10) break;
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
