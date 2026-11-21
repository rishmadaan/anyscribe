// A stand-in for `python -m anyscribe ui --port N --no-open [--watch-stdin]`, for the tests.
// FAKE_MODE: ok | exit-early | crash | silent | stubborn (ignores stdin and SIGTERM) | impostor (answers
// health with another pid) | die-before-ready (starts its helpers, then exits 1 without serving). FAKE_JOBS: JSON for /api/jobs
// (unset: 404). FAKE_JOBS_ANSWERS=N: answer /api/jobs N times, then never again. Any POST is
// written to stderr ("fake got POST …"). FAKE_GRANDCHILD=1: start a helper that ignores SIGTERM and print its pid.
// FAKE_JOBS_STATUS: its HTTP status; FAKE_JOBS_DELAY_MS: answer that late.
'use strict';

const http = require('node:http');

const args = process.argv.slice(2);
const port = Number(args[args.indexOf('--port') + 1]);
const watch = args.includes('--watch-stdin');
const mode = process.env.FAKE_MODE || 'ok';

if (mode === 'exit-early') {
  process.stderr.write("Traceback (most recent call last):\nPermissionError: [Errno 13] Permission denied: '/home/x/.anyscribe/config.yaml'\n");
  process.exit(1);
}

let answers = 0;
function serve(listenPort) {
  const server = http.createServer((req, res) => {
    if (req.url === '/api/health') {
      res.setHeader('content-type', 'application/json');
      const pid = mode === 'impostor' ? process.pid + 1 : process.pid;
      return res.end(JSON.stringify({ app: 'anyscribe', ok: true, pid }));
    }
    if (req.method === 'POST') process.stderr.write(`fake got POST ${req.url}\n`);
    if (req.url === '/api/jobs' && process.env.FAKE_JOBS_ANSWERS !== undefined && answers++ >= Number(process.env.FAKE_JOBS_ANSWERS)) {
      return; // never answers again
    }
    if (req.url === '/api/jobs' && process.env.FAKE_JOBS) {
      res.statusCode = Number(process.env.FAKE_JOBS_STATUS || 200);
      res.setHeader('content-type', 'application/json');
      return setTimeout(() => res.end(process.env.FAKE_JOBS), Number(process.env.FAKE_JOBS_DELAY_MS || 0));
    }
    if (req.url === '/') {
      res.setHeader('content-type', 'text/html');
      return res.end('<!doctype html><title>fake dashboard</title><div id="root"><p>fake</p></div>');
    }
    if (req.url === '/redirect-out') {
      res.writeHead(302, { location: 'http://example.invalid/away' });
      return res.end();
    }
    res.statusCode = 404;
    res.end('{}');
  });
  server.listen(listenPort, '127.0.0.1');
  return server;
}

console.log(`anyscribe ui → http://127.0.0.1:${port}`);
if (mode !== 'silent' && mode !== 'die-before-ready') serve(port);
if (process.env.FAKE_GRANDCHILD) {
  const helper = require('node:child_process').spawn(process.execPath, ['-e', "process.on('SIGTERM', () => {}); setInterval(() => {}, 1 << 30)"], { stdio: 'ignore' });
  console.log(`grandchild pid ${helper.pid}`);
}
if (mode === 'die-before-ready') setTimeout(() => process.exit(1), 200);
if (mode === 'crash') setTimeout(() => process.exit(1), 300);
if (watch && mode !== 'stubborn') process.stdin.on('end', () => process.exit(0)).resume();
if (mode === 'stubborn' || mode === 'silent') process.on('SIGTERM', () => {});
setInterval(() => {}, 1 << 30); // stay alive until told otherwise
