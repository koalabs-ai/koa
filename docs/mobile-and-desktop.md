# Path to phone and desktop

| Step | What | Status |
|---|---|---|
| 1 | **PWA**: the `koa-core serve` UI ships with a manifest and a service worker; installable from the browser | done |
| 2 | **Pairing devices**: `koa-core pair` shows a short-lived code (and a QR if `qrencode` is present); the device exchanges it for its own revocable token | done |
| 3 | **Android**: Capacitor packages the same UI; the app asks for your KOA's URL and pairs | to do |
| 4 | **Desktop**: Tauri with koa-core as an internal process (`.deb`, `.AppImage`, `.dmg`/`.app`) | to do |
| 5 | **iOS / App Store**: developer account, privacy policy, account deletion from the app | decision pending |
| 6 | **Syncing** between devices without a third-party server: git, Syncthing, or a relay of your own | design |

Principles:
- The app never requires a specific VPN: app stores reject that, and it
  breaks the idea of not depending on anyone.
- The phone is a client of **your** KOA; there's no intermediate cloud.
- No domain cookies or messaging codes as the sole method: a per-device
  token is what works the same on web, Android, iOS, and desktop.

## How pairing turned out (step 2)

`koa-core pair [--admin] [--url URL]` creates an 8-character code (format
`XXXX-XXXX`, alphabet without `0/O/1/I` so it can be read aloud), valid for 10
minutes and single-use; only its sha256 is stored. The device exchanges it
for its own token (`kd_…`, also only its hash stays on disk) by calling
`POST /v1/pair/claim` — over HTTP at `/pair#code=XXXX-XXXX` (the same SPA as
`koa-core serve`, no native app needed) or by pasting it into the "Connect
this device" screen that shows up if the stored token is no longer valid.

With a master token or an active device, every `/v1/*` request (except
`/v1/health` and `POST /v1/pair/claim` itself) requires
`Authorization: Bearer <token>`; without either, it stays open on loopback
as always. A device marked `--admin` can pair others and view/revoke the
list (`koa-core devices list|revoke <id>`, or the "Devices" tab in the app);
a regular one only uses the API. Ten failed code attempts in 10 minutes
block further attempts with 429 for that window.

With this, step 3 (Android/Capacitor) and step 4 (desktop/Tauri) already
have something to authenticate with: they ask for your KOA's URL, open
`/pair` inside a webview, and end up paired just like a browser.
