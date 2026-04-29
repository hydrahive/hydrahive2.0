const BACKEND_URL = process.env.HH_WA_BACKEND_URL || "http://127.0.0.1:8001";
const SECRET = process.env.HH_WA_BRIDGE_SECRET || "";

export async function pushIncoming(payload) {
  const url = `${BACKEND_URL}/api/communication/whatsapp/incoming`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-HH-Bridge-Secret": SECRET,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      console.error(`[push] Backend antwortet ${res.status}`);
    }
  } catch (err) {
    console.error(`[push] Fehler: ${err.message}`);
  }
}
