import path from "node:path";
import fs from "node:fs/promises";
import { useMultiFileAuthState } from "@whiskeysockets/baileys";

function dataDir() {
  const d = process.env.HH_WA_DATA_DIR;
  if (!d) throw new Error("HH_WA_DATA_DIR nicht gesetzt");
  return d;
}

export async function authStateFor(user) {
  const dir = path.join(dataDir(), user, "auth");
  await fs.mkdir(dir, { recursive: true });
  return useMultiFileAuthState(dir);
}

export async function clearAuth(user) {
  const dir = path.join(dataDir(), user);
  await fs.rm(dir, { recursive: true, force: true });
}
