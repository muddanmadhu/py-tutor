/**
 * Routing rules for the local static host.
 *
 *   node --test tools/static_server.test.mjs
 *
 * Drives the handler with mock request and response objects rather than over a
 * socket: the rules are the interesting part, and a restricted environment may
 * refuse to bind a port — which would silently skip the only coverage this has.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { createRequestHandler } from './static_server.mjs';

const DIST = resolve(new URL('../frontend/dist', import.meta.url).pathname);
const handler = createRequestHandler(DIST);

/** Run one request through the handler and collect what came back. */
function request(url, method = 'GET') {
  return new Promise((done) => {
    const chunks = [];
    const res = {
      statusCode: null,
      headers: {},
      writeHead(status, headers) {
        this.statusCode = status;
        // Header names are case-insensitive; normalise so assertions can be too.
        for (const [k, v] of Object.entries(headers ?? {})) {
          this.headers[k.toLowerCase()] = v;
        }
        return this;
      },
      end(body) {
        if (body) chunks.push(Buffer.from(body));
        done({ status: this.statusCode, headers: this.headers, body: Buffer.concat(chunks) });
      },
      // createReadStream(...).pipe(res) drives these.
      on() {},
      once() {},
      emit() {},
      write(chunk) {
        chunks.push(Buffer.from(chunk));
        return true;
      },
    };
    handler({ url, method, headers: { host: 'localhost:4173' } }, res);
  });
}

test('serves index.html at the root', async () => {
  const res = await request('/');
  assert.equal(res.status, 200);
  assert.match(res.headers['content-type'], /text\/html/);
});

test('deep links fall back to index.html with a 200, so a reload works', async () => {
  for (const route of ['/learn', '/learn/what-python-is', '/practice/fizzbuzz', '/dashboard']) {
    const res = await request(route);
    assert.equal(res.status, 200, `${route} should serve the app`);
    assert.match(res.headers['content-type'], /text\/html/, `${route} should be HTML`);
  }
});

test('a missing file with an extension 404s instead of returning HTML', async () => {
  // Returning index.html here is what produces "Unexpected token '<'" in the
  // console and hides the real cause, so the honest 404 is the contract.
  const res = await request('/assets/does-not-exist.js');
  assert.equal(res.status, 404);
});

test('the curriculum and vendored Python are served with the right types', async () => {
  const json = await request('/content/courses.json');
  assert.equal(json.status, 200);
  assert.match(json.headers['content-type'], /application\/json/);

  for (const file of ['/content/grader.py', '/content/reviewer.py']) {
    const res = await request(file);
    assert.equal(res.status, 200, `${file} must be served; grading needs it`);
    assert.match(res.headers['content-type'], /text\/plain/);
  }
});

test('cache headers match the production host', async () => {
  const content = await request('/content/courses.json');
  assert.equal(content.headers['cache-control'], 'public, max-age=0, must-revalidate');

  const page = await request('/');
  assert.equal(page.headers['cache-control'], 'no-cache');
});

test('fingerprinted assets are immutable', async () => {
  const { readdir } = await import('node:fs/promises');
  const assets = await readdir(resolve(DIST, 'assets'));
  const js = assets.find((f) => f.endsWith('.js'));
  assert.ok(js, 'the build should emit at least one JS asset');

  const res = await request(`/assets/${js}`);
  assert.equal(res.status, 200);
  assert.equal(res.headers['cache-control'], 'public, max-age=31536000, immutable');
  assert.match(res.headers['content-type'], /text\/javascript/);
});

test('security headers are present on every response', async () => {
  const res = await request('/');
  assert.equal(res.headers['x-content-type-options'], 'nosniff');
  assert.equal(res.headers['x-frame-options'], 'DENY');
  assert.equal(res.headers['referrer-policy'], 'strict-origin-when-cross-origin');
});

test('path traversal cannot escape the bundle', async () => {
  const { readFile } = await import('node:fs/promises');
  const index = await readFile(resolve(DIST, 'index.html'), 'utf8');
  const secret = await readFile(resolve(DIST, '..', '..', '.env'), 'utf8').catch(() => null);

  // Plain, encoded, and double-encoded — the second is what a naive check that
  // looks for the literal ".." in the URL string misses.
  //
  // Asserting on the *body*, not the status. These all currently answer 200
  // with index.html, because Node's extname() returns '' for a dotfile, so the
  // SPA fallback treats /.env as a client route. That is harmless but it means
  // a status assertion would pass while a real escape also returned 200 — the
  // property worth pinning is that nothing above the bundle is ever the body.
  for (const attack of [
    '/../.env',
    '/../../.env',
    '/%2e%2e/.env',
    '/assets/../../.env',
    '/%252e%252e/.env',
    '/../package.json',
    '/../../backend/app/core/config.py',
  ]) {
    const res = await request(attack);
    const body = res.body.toString('utf8');
    assert.ok(
      res.status === 404 || body === index,
      `${attack} served something other than a 404 or the app shell`,
    );
    if (secret) {
      assert.ok(!body.includes('PYFORGE_SECRET_KEY'), `${attack} leaked .env`);
    }
  }
});

test('writes are refused', async () => {
  const res = await request('/', 'POST');
  assert.equal(res.status, 405);
});
