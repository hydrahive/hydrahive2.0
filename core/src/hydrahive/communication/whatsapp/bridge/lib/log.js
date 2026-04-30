/**
 * Geteilter pino-Logger für die Bridge.
 *
 * Output ist NDJSON via stdout, was process.py:_pump als ganze Zeilen
 * an den Python-Logger weiterreicht. Level kommt aus HH_WA_BRIDGE_LOG_LEVEL,
 * default "info".
 *
 * Baileys-interner Logger (sock.js) braucht ein Logger-Objekt mit child(),
 * deshalb hier auch ein "baileys"-Child mit eigenem Level (warn) damit
 * Baileys nicht alles rausspamt.
 */
import pino from "pino";

const LEVEL = (process.env.HH_WA_BRIDGE_LOG_LEVEL || "info").toLowerCase();

export const logger = pino({
  level: LEVEL,
  base: { component: "wa-bridge" },
  timestamp: pino.stdTimeFunctions.isoTime,
});

// Baileys ist sehr gesprächig — eigener Level damit der Hauptlogger
// nicht überschwemmt wird.
export const baileysLogger = pino({
  level: process.env.HH_WA_BRIDGE_BAILEYS_LEVEL || "warn",
  base: { component: "baileys" },
  timestamp: pino.stdTimeFunctions.isoTime,
});
