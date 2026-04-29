import QRCode from "qrcode";

export async function qrToDataUrl(qrString) {
  return QRCode.toDataURL(qrString, {
    errorCorrectionLevel: "M",
    margin: 1,
    scale: 6,
  });
}
