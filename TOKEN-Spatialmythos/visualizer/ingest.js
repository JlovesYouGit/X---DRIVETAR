// Run this to receive particle JSON from the simulator (piped via stdin) and broadcast to the browser.
// Usage:
//   dotnet run -c Debug --no-build | node ingest.js
// Then open:
//   http://localhost:5173/ (or open index.html directly)

import http from 'http';
import WebSocket, { WebSocketServer } from 'ws';

const PORT_WS = 8787;

const wss = new WebSocketServer({ port: PORT_WS });

function broadcast(obj) {
  const data = JSON.stringify(obj);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) client.send(data);
  }
}

console.log(`[ingest] WebSocket server listening on ws://localhost:${PORT_WS}`);
console.log('[ingest] Waiting for simulator JSON lines on stdin...');

let buffer = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => {
  buffer += chunk;
  // Accept line-delimited JSON
  let idx;
  while ((idx = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    try {
      const msg = JSON.parse(line);
      // Basic validation
      if (msg && Array.isArray(msg.particles)) {
        broadcast(msg);
      }
    } catch {
      // ignore non-JSON lines from the simulator
    }
  }
});

