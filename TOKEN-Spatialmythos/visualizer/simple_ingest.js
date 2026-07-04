// No external deps version: broadcasts line-delimited JSON to the browser via SSE.
// Start it in one terminal:
//   node visualizer/simple_ingest.js
// Then run the simulator and pipe stdout into it:
//   dotnet run -c Debug --no-build | node visualizer/simple_ingest.js
// Finally open: visualizer/index.html (it will use EventSource at /events)

import http from 'http';

const PORT = 8787;

let lastMsg = null;
const clients = new Set();

function sendSse(res, data) {
  res.write(`data: ${JSON.stringify(data)}\n\n`);
}

const server = http.createServer((req, res) => {
  if (req.url === '/events') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });
    res.write('\n');

    if (lastMsg) sendSse(res, lastMsg);

    clients.add(res);
    req.on('close', () => clients.delete(res));
    return;
  }

  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('simple_ingest running');
});

server.listen(PORT, () => {
  console.log(`[simple_ingest] Listening for SSE at http://localhost:${PORT}/events`);
});

let buffer = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buffer += chunk;
  let idx;
  while ((idx = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    try {
      const msg = JSON.parse(line);
      lastMsg = msg;
      for (const res of clients) {
        try { sendSse(res, msg); } catch {}
      }
    } catch {
      // ignore
    }
  }
});

