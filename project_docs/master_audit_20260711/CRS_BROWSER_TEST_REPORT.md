# CRS Browser Test Report

## Result

Status: **BLOCKED FOR LIVE LOCAL BROWSER INSPECTION**.

The earlier configured browser connector rejected `http://127.0.0.1:5000` under its security policy. A 2026-07-11 retry with the installed in-app browser plugin could not start because the plugin's required `scripts/browser-client.mjs` file is absent. The plugin instructions prohibit switching to another browser-control surface as a workaround, so no bypass was attempted.

## Automated Substitute Evidence

| Check | Result |
|---|---|
| Jinja template compilation | Pass, 61 templates |
| CSS imports | Pass |
| CSS brace balance | Pass |
| Literal template links | Pass |
| Unauthenticated GET route smoke | Pass, no 500 response |
| Login page | Pass, HTTP 200 |
| Missing CSRF token | Pass, HTTP 400 |
| Branded not-found page | Pass, HTTP 404 |
| Required security headers | Pass |

## Not Proven

- Screenshot appearance and visual regression.
- Client-side interaction in a real browser.
- Responsive layout at required viewports.
- Authenticated role workflows.
- Download/upload progress rendering during live PLC operations.

These remain P0 acceptance evidence before production approval.
