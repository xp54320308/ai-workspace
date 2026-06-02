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

function extractNews(html) {
  const items = [];
  // Try <a> with title attribute or meaningful text
  const re = /<a[^>]*href=["']([^"']*)["'][^>]*(?:title=["']([^"']{8,120})["'])?[^>]*>([^<]{8,80})<\/a>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const text = (m[2] || m[3] || '').trim();
    const href = m[1];
    if (text && text.match(/[\u4e00-\u9fff]/) && text.length >= 8 && !text.match(/^(首页|登录|注册|更多|关于|联系|下载|APP|客户端)/)) {
      items.push({ title: text, url: href });
    }
    if (items.length >= 15) break;
  }
  return items;
}

async function main() {
  const sources = [
    { name: '澎湃新闻', url: 'https://www.thepaper.cn/' },
    { name: '腾讯新闻', url: 'https://news.qq.com/' },
    { name: 'TechCrunch', url: 'https://techcrunch.com/' },
    { name: 'TheVerge', url: 'https://www.theverge.com/' },
  ];

  for (const s of sources) {
    try {
      const html = await fetch(s.url);
      const items = extractNews(html);
      console.log('### ' + s.name);
      items.slice(0, 8).forEach((item, i) => console.log((i+1) + '. ' + item.title));
      if (items.length === 0) console.log('(无法提取, 长度: ' + html.length + ')');
      console.log('');
    } catch (e) {
      console.log('### ' + s.name + ' - 错误: ' + e.message);
      console.log('');
    }
  }
}

main();
