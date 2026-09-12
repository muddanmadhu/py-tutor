/**
 * Static host for the built bundle — Node stdlib only, nothing to install.
 *
 *   node tools/static_server.mjs [--dir frontend/dist] [--port 4173] [--host 127.0.0.1]
 *
 * By default it listens on both loopback addresses, 127.0.0.1 and ::1, because
 * `localhost` resolves to ::1 ahead of 127.0.0.1 on macOS: binding only IPv4
 * leaves a browser that follows that order reporting ERR_CONNECTION_REFUSED
 * while the server is up and answering on an address nothing asked for. It
 * stays loopback-only either way — `--host` overrides with a single address.
 *
 * `python3 -m http.server` is the obvious alternative and it is wrong for this
 * app: it has no SPA fallback, so every deep link (/learn/loops, /practice/...)
 * returns 404 and the router never gets a chance to handle it. Reloading any
 * page but the home page appears to break the site.
 *
 * The behaviour here is deliberately the same as the production hosts, so that
 * "it worked locally" means something:
 *
 *   - unknown routes rewrite to index.html with a 200, like render.yaml
 *   - /assets/* is immutable (Vite fingerprints those names)
 *   - /content/* must revalidate (regenerated each build, stable names)
 *   - nosniff / DENY / strict-origin-when-cross-origin, as render.yaml sets
 *
 * No COOP/COEP, also matching render.yaml: cross-origin isolation would block
 * the Pyodide fetch from jsDelivr and nothing would run.
 */

import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { join, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

// --- content types ---------------------------------------------------------

// Explicit rather than a lookup dependency. A wrong or missing type on .js or
// .mjs makes the browser refuse the module outright, which reads as a blank
// page with one console line, so the ones this bundle actually emits are here.
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  // The vendored grader and reviewer. text/plain so a browser that follows a
  // link to one displays it instead of offering a download.
  '.py': 'text/plain; charset=utf-8',
  '.wasm': 'application/wasm',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
};

function cacheControl(urlPath) {
  if (urlPath.startsWith('/assets/')) return 'public, max-age=31536000, immutable';
  if (urlPath.startsWith('/content/')) return 'public, max-age=0, must-revalidate';
  return 'no-cache';
}

// --- request handling ------------------------------------------------------

/**
 * Build the request handler for a bundle directory.
 *
 * Exported, and taking `root` as an argument rather than reading a module-level
 * constant, so the routing rules can be tested without binding a port — which
 * a restricted environment may not allow, and which would otherwise make this
 * file the one part of the local host that nothing checks.
 */
export function createRequestHandler(root) {
  /** Resolve a URL path to a file inside `root`, or null if it escapes or is absent. */
  async function resolveFile(urlPath) {
    // decodeURIComponent so a lesson slug with an escaped character still finds
    // its file; the containment check below is what keeps `..` and encoded
    // variants of it from reaching outside the bundle.
    let decoded;
    try {
      decoded = decodeURIComponent(urlPath);
    } catch {
      return null;
    }

    const candidate = resolve(join(root, decoded));
    if (candidate !== root && !candidate.startsWith(root + sep)) return null;

    try {
      const info = await stat(candidate);
      if (info.isDirectory()) return resolveFile(join(urlPath, 'index.html'));
      return { path: candidate, size: info.size };
    } catch {
      return null;
    }
  }

  function send(res, status, file, urlPath) {
    res.writeHead(status, {
      'Content-Type': TYPES[extname(file.path).toLowerCase()] ?? 'application/octet-stream',
      'Content-Length': file.size,
      'Cache-Control': cacheControl(urlPath),
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    });
    createReadStream(file.path).pipe(res);
  }

  const handler = async (req, res) => {
    const urlPath = new URL(req.url, `http://${req.headers.host ?? 'localhost'}`).pathname;

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405, { Allow: 'GET, HEAD' });
      res.end('Method Not Allowed');
      return;
    }

    const file = await resolveFile(urlPath);
    if (file) {
      send(res, 200, file, urlPath);
      return;
    }

    // The SPA fallback, narrowed. render.yaml rewrites everything, but doing
    // that here would answer a mistyped /assets/index-abc123.js with HTML, and
    // the browser reports that as "Unexpected token '<'" — which sends you
    // looking at the bundle instead of at the missing file. A path with a file
    // extension is asking for a file, so let it 404 honestly; anything else is
    // a client route.
    if (!extname(urlPath)) {
      const index = await resolveFile('/index.html');
      if (index) {
        send(res, 200, index, '/');
        return;
      }
    }

    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end(`404 Not Found: ${urlPath}\n`);
  };

  handler.resolveFile = resolveFile;
  return handler;
}

// --- startup ---------------------------------------------------------------

/** Only when run as a program; importing this file must not bind anything. */
async function main() {
  const argv = process.argv.slice(2);
  const flag = (name, fallback) => {
    const i = argv.indexOf(`--${name}`);
    return i !== -1 && argv[i + 1] ? argv[i + 1] : fallback;
  };

  const root = resolve(flag('dir', 'frontend/dist'));
  const port = Number(flag('port', process.env.PORT || 4173));
  // Null rather than a default, so we can tell "user asked for one address"
  // from "bind the usual pair".
  const explicitHost = flag('host', null);
  const hosts = explicitHost ? [explicitHost] : ['127.0.0.1', '::1'];

  const handler = createRequestHandler(root);

  if (!(await handler.resolveFile('/index.html'))) {
    console.error(`xx  No index.html in ${root} — build first: cd frontend && npm run build:root`);
    process.exit(1);
  }

  /**
   * Bind one address, resolving to the listening server.
   *
   * A loopback family this machine has not configured resolves to null instead
   * of rejecting: with IPv6 disabled there is no ::1 to bind, and the IPv4
   * listener alone still serves the site. Anything else rejects, including a
   * port collision on only one of the two — falling back to serving on half
   * the pair would recreate exactly the confusion this function exists to fix.
   */
  function listenOn(host) {
    return new Promise((ok, fail) => {
      const server = createServer(handler);
      server.once('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          fail(new Error(`Port ${port} is already in use on ${host}. Pick another: --port ${port + 1}`));
        } else if (err.code === 'EACCES' || err.code === 'EPERM') {
          fail(new Error(
            `Not permitted to bind port ${port}. A sandbox that forbids\n` +
            '    listening sockets will do this; run from a normal terminal.'));
        } else if (err.code === 'EAFNOSUPPORT' || err.code === 'EADDRNOTAVAIL') {
          ok(null);
        } else {
          fail(err);
        }
      });
      server.listen(port, host, () => ok(server));
    });
  }

  let servers = [];
  try {
    servers = (await Promise.all(hosts.map(listenOn))).filter(Boolean);
  } catch (err) {
    console.error(`xx  ${err.message}`);
    process.exit(1);
  }

  if (servers.length === 0) {
    console.error(`xx  Could not bind ${hosts.join(' or ')} on port ${port}.`);
    process.exit(1);
  }

  // Only advertise `localhost` when both loopback addresses are answering;
  // otherwise name the address actually bound, since that is the one that
  // works regardless of how this machine orders its resolution.
  const bound = servers.map((s) => s.address());
  const addresses = bound
    .map((a) => (a.family === 'IPv6' ? `[${a.address}]` : a.address))
    .join(' and ');
  const url = !explicitHost && servers.length > 1
    ? `http://localhost:${port}/`
    : `http://${bound[0].family === 'IPv6' ? `[${bound[0].address}]` : bound[0].address}:${port}/`;

  console.log(`
  ────────────────────────────────────────────────────────────────
   PyForge — static build, served locally

     Web app     ${url}
     Listening   ${addresses} on port ${port}
     Serving     ${root}

     No backend, no database, no accounts. Python runs in your
     browser under Pyodide, which is fetched from jsDelivr on the
     first run — so the first Run needs a network connection.

     Progress lives in this browser's localStorage.

   Ctrl-C to stop.
  ────────────────────────────────────────────────────────────────
`);

  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => {
      for (const server of servers) server.close();
      process.exit(0);
    });
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}

