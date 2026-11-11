// Node only. Opens an HTTPS connection to one fixed IP address and keeps the host name
// for TLS and the Host header. The upload tool uses it so that the address that passed
// the public-address check is the address that receives the request. A DNS record that
// changes after the check has no effect.
import { request } from 'node:https';
import { isIP } from 'node:net';

export function pinnedLookup(ip) {
  const family = isIP(ip);
  if (!family) throw new Error(`Not an IP address: ${ip}`);
  return (_hostname, options, callback) =>
    options?.all ? callback(null, [{ address: ip, family }]) : callback(null, ip, family);
}

// Collects response chunks and refuses the chunk that takes the total over the limit.
export function createByteCollector(maxBytes) {
  const chunks = [];
  let size = 0;
  return {
    add(chunk) {
      size += chunk.length;
      if (size > maxBytes) return false;
      chunks.push(chunk);
      return true;
    },
    bytes: () => Buffer.concat(chunks),
  };
}

export function pinnedFetch(url, init = {}, ip, maxBytes = 64 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const req = request(
      {
        host: u.hostname,
        servername: u.hostname,
        port: 443,
        path: u.pathname + u.search,
        method: init.method || 'GET',
        headers: init.headers,
        lookup: pinnedLookup(ip),
        agent: false,
      },
      (res) => {
        const collector = createByteCollector(maxBytes);
        let overLimit = false;
        res.on('data', (chunk) => {
          if (overLimit || collector.add(chunk)) return;
          // Reject here. The 'end' event can still fire after destroy when the body came in one chunk.
          overLimit = true;
          reject(new Error(`Response is larger than ${maxBytes} bytes`));
          req.destroy();
        });
        res.on('error', reject);
        res.on('end', () => {
          if (overLimit) return;
          const headers = new Headers();
          for (const [k, v] of Object.entries(res.headers)) headers.set(k, Array.isArray(v) ? v.join(', ') : String(v));
          const empty = res.statusCode === 204 || res.statusCode === 304 || (res.statusCode >= 300 && res.statusCode < 400);
          resolve(new Response(empty ? null : collector.bytes(), { status: res.statusCode, headers }));
        });
      },
    );
    req.on('error', reject);
    req.setTimeout(120000, () => req.destroy(new Error('Upload connection timed out')));
    if (init.body) req.write(Buffer.from(init.body));
    req.end();
  });
}
