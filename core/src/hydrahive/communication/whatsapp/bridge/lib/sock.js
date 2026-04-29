import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
} from "@whiskeysockets/baileys";
import pino from "pino";
import { authStateFor, clearAuth } from "./auth.js";
import { qrToDataUrl } from "./qr.js";
import { pushIncoming } from "./push.js";

const sockets = new Map();
const explicitlyDisconnected = new Set();
const logger = pino({ level: "warn" });
const LOOP_MARKER = "​";

export function getStatus(user) {
  const s = sockets.get(user);
  if (!s) return { connected: false, state: "disconnected" };
  return {
    connected: s.connected,
    state: s.state,
    phone: s.phone,
    qr_data_url: s.qr_data_url,
  };
}

export async function connect(user) {
  explicitlyDisconnected.delete(user);
  const existing = sockets.get(user);
  if (existing && (existing.connected || existing.state === "connecting" || existing.state === "waiting_qr")) {
    return getStatus(user);
  }

  const entry = { connected: false, state: "connecting", phone: null, qr_data_url: null, sock: null };
  sockets.set(user, entry);

  const { state: authState, saveCreds } = await authStateFor(user);
  const { version } = await fetchLatestBaileysVersion();
  const sock = makeWASocket({
    version,
    auth: authState,
    logger,
    printQRInTerminal: false,
    browser: ["HydraHive2", "Chrome", "1.0"],
  });
  entry.sock = sock;

  sock.ev.on("creds.update", saveCreds);
  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      entry.state = "waiting_qr";
      entry.qr_data_url = await qrToDataUrl(qr);
    }
    if (connection === "open") {
      entry.connected = true;
      entry.state = "connected";
      entry.qr_data_url = null;
      entry.phone = sock.user?.id?.split(":")[0]?.split("@")[0] || null;
    } else if (connection === "close") {
      const code = lastDisconnect?.error?.output?.statusCode;
      entry.connected = false;
      entry.state = "disconnected";
      sockets.delete(user);
      if (code === DisconnectReason.loggedOut) {
        await clearAuth(user);
        explicitlyDisconnected.add(user);
      }
      const wasExplicit = explicitlyDisconnected.has(user);
      if (!wasExplicit) {
        const delay = code === DisconnectReason.restartRequired ? 200 : 2000;
        setTimeout(() => connect(user).catch((e) => logger.error({ err: e }, "reconnect")), delay);
      }
    }
  });

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const m of messages) {
      if (m.key.fromMe) continue;
      const rawJid = m.key.remoteJid || "";
      if (!rawJid || rawJid === "status@broadcast" || rawJid.endsWith("@broadcast")) continue;
      if (m.messageStubType) continue;
      const text = m.message?.conversation || m.message?.extendedTextMessage?.text || "";
      if (!text) continue;
      if (text.includes(LOOP_MARKER)) continue;
      const isGroup = rawJid.endsWith("@g.us");
      const jid = !isGroup && rawJid.endsWith("@lid") && m.key.senderPn
        ? m.key.senderPn
        : rawJid;
      const participant = isGroup
        ? ((m.key.participant?.endsWith("@lid") && m.key.participantPn)
            ? m.key.participantPn
            : (m.key.participant || null))
        : null;
      await pushIncoming({
        target_username: user,
        external_user_id: jid,
        participant,
        is_group: isGroup,
        sender_name: m.pushName || null,
        text,
      });
    }
  });

  return getStatus(user);
}

export async function disconnect(user) {
  explicitlyDisconnected.add(user);
  const s = sockets.get(user);
  if (s?.sock) {
    try { await s.sock.logout(); } catch { /* ignore */ }
  }
  sockets.delete(user);
  await clearAuth(user);
}

export async function send(user, to, text) {
  const s = sockets.get(user);
  if (!s || !s.connected) throw new Error("nicht verbunden");
  await s.sock.sendMessage(to, { text: text + LOOP_MARKER });
}
