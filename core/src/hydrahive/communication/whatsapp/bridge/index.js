import http from "node:http";
import { connect, disconnect, send, sendAudio, getStatus } from "./lib/sock.js";
import { logger } from "./lib/log.js";

const PORT = parseInt(process.env.HH_WA_BRIDGE_PORT || "8767", 10);
const HOST = "127.0.0.1";

function sendJson(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => {
      if (!data) return resolve({});
      try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
    });
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${HOST}`);
    const mConnect = url.pathname.match(/^\/connect\/([^/]+)$/);
    const mDisconnect = url.pathname.match(/^\/disconnect\/([^/]+)$/);
    const mStatus = url.pathname.match(/^\/status\/([^/]+)$/);
    const mSend = url.pathname.match(/^\/send\/([^/]+)$/);

    if (req.method === "GET" && url.pathname === "/healthz") {
      return sendJson(res, 200, { ok: true });
    }
    if (req.method === "POST" && mConnect) {
      const status = await connect(decodeURIComponent(mConnect[1]));
      return sendJson(res, 200, status);
    }
    if (req.method === "POST" && mDisconnect) {
      await disconnect(decodeURIComponent(mDisconnect[1]));
      return sendJson(res, 200, { ok: true });
    }
    if (req.method === "GET" && mStatus) {
      return sendJson(res, 200, getStatus(decodeURIComponent(mStatus[1])));
    }
    if (req.method === "POST" && mSend) {
      const body = await readBody(req);
      if (!body.to) return sendJson(res, 400, { error: "to erforderlich" });
      const user = decodeURIComponent(mSend[1]);
      if (body.audio_base64) {
        const buf = Buffer.from(body.audio_base64, "base64");
        const opts = {};
        if (typeof body.seconds === "number") opts.seconds = body.seconds;
        if (body.waveform_base64) opts.waveform = Buffer.from(body.waveform_base64, "base64");
        await sendAudio(user, body.to, buf, opts);
        return sendJson(res, 200, { ok: true, audio: true });
      }
      if (!body.text) return sendJson(res, 400, { error: "text oder audio_base64 erforderlich" });
      await send(user, body.to, body.text);
      return sendJson(res, 200, { ok: true });
    }
    sendJson(res, 404, { error: "not_found" });
  } catch (err) {
    logger.error({ err: err.message, stack: err.stack }, "Bridge-Request Fehler");
    sendJson(res, 500, { error: err.message });
  }
});

server.listen(PORT, HOST, () => {
  logger.info({ host: HOST, port: PORT }, "WhatsApp-Bridge läuft");
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    logger.info({ signal: sig }, "Shutdown");
    server.close(() => process.exit(0));
  });
}
