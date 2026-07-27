# Absicherung einer öffentlich erreichbaren Instanz

Stand: 27.07.2026. Geprüft an der ersten Internet-Testinstanz hinter Cloudflare.

## Was der Installer bereits mitbringt

- HTTP (Port 80) leitet auf HTTPS um — **außer** `/api/health-data/` (Ingest
  von Geräten ohne TLS)
- TLS nur 1.2/1.3, `HIGH:!aNULL:!MD5`
- CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`,
  `Permissions-Policy`
- **HSTS** (neu, `max-age=31536000`)
- **HTTPS-Erzwingung hinter einem Proxy** (neu, siehe unten)
- Login-Sperre pro Benutzer *und* IP (`lockout`), HTTP 429
- API-Doku (`/api/docs`, `/api/openapi.json`) nur wenn ausdrücklich aktiviert
- CORS: Default nur `localhost` — fremde Origins bekommen kein `allow-origin`

## Der Proxy-Fall

Steht ein Reverse-Proxy davor (Cloudflare, Traefik …), endet TLS an dessen
Rand. Der Port-80-Block von nginx greift dann **nicht**, weil der Proxy Port 80
selbst beantwortet und die Anfrage intern weiterreicht.

Deshalb prüft der HTTPS-Block zusätzlich `X-Forwarded-Proto`:

```nginx
if ($http_x_forwarded_proto = "http") {
    return 301 https://$host$request_uri;
}
```

Ohne Proxy ist der Header leer und die Regel greift nie — lokale Installationen
laufen unverändert.

> **Wichtig:** Dieser Header ist nur vertrauenswürdig, wenn ausschließlich der
> Proxy den Server erreichen kann. Ist der Ursprungsserver direkt erreichbar,
> kann ihn jeder setzen. Siehe Checkliste unten.

## Checkliste vor dem Livegang

### Beim Proxy (Cloudflare)

- [ ] **Always Use HTTPS** aktivieren — sonst beantwortet Cloudflare
      HTTP-Anfragen selbst und liefert die Seite unverschlüsselt aus
- [ ] SSL-Modus auf **Full (strict)**, nicht „Flexible" (dort ist die Strecke
      Proxy → Server unverschlüsselt)
- [ ] Rate Limiting auf `/api/auth/login`

### Am Ursprungsserver

- [ ] Firewall: Port 80/443 **nur** für Cloudflare-Adressbereiche öffnen.
      Sonst ist der Proxy umgehbar und alle Regeln dort sind wirkungslos.
- [ ] Prüfen, ob die Server-IP über alte DNS-Einträge auffindbar ist
      (Subdomains, MX, TXT)

### Konfiguration

- [ ] `HH_JWT_EXPIRE_MINUTES` senken — Default 1440 (24 h) ist für eine
      öffentliche Instanz lang; 60–120 sind angemessener
- [ ] `HH_CORS_ORIGINS` setzen, falls ein anderes Frontend zugreift
- [ ] Prüfen, dass `/api/docs` nicht aktiviert ist

## Bekannte, bewusst akzeptierte Punkte

- **`unsafe-eval` in der CSP** — three.js und d3 nutzen `new Function()`.
  Schwächt den XSS-Schutz; ohne Umbau dieser Abhängigkeiten nicht entfernbar.
- **`/api/health` ist ohne Login lesbar** und nennt Version + Commit-Hash. Für
  Uptime-Prüfungen praktisch, verrät aber den genauen Stand.
