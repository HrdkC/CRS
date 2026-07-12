# CRS Roadmap Modernization Implementation - 2026-07-12

## Decision

CRS remains a server-rendered Flask/Jinja application. A SPA rewrite is rejected because it would increase deployment, security, testing, and plant-support risk without improving the PLC safety boundary. Modernization will be progressive and reversible.

## Implemented In This Pass

### Frontend delivery

- Added `scripts/build_css_bundle.py` as the single source-controlled build step for the ordered CSS module manifest.
- Kept the 25 editable CSS modules, while production now serves `css/crs.bundle.css` as one request instead of a 25-file `@import` chain.
- Integrated the bundle build into `setup_crs.bat`.
- Added a stale/missing bundle failure to `scripts/validate_crs_release.py`.

### Progressive interaction pilot

- Added locally hosted HTMX 2.0.10 with its upstream MIT license and verified SHA-384 integrity value.
- Audit filters and server-side sorting now update the audit result region without a full navigation.
- Ordinary GET forms and links remain the fallback when JavaScript is unavailable.
- Added an accessible live status message for in-progress, completed, and failed updates.
- Session expiry during an HTMX request redirects to login rather than inserting the login page into a result panel.

### Security and maintainability

- Moved initial theme/font bootstrap out of inline HTML into `theme-bootstrap.js`.
- Moved recipe machine/stage selector behavior out of inline template JavaScript into the shared CRS runtime.
- Externalized all remaining template JavaScript into three page modules plus the shared CRS runtime.
- Removed inline event-handler attributes and tightened CSP to `script-src 'self'` without `unsafe-inline`.
- Added a setup-managed, ignored machine-local session secret so development no longer relies on the hardcoded fallback.
- Improved PLC buffer status polling: no overlapping requests, reduced hidden-tab polling, terminal-state shutdown, and safe retry during transient status connectivity loss.
- Added safe regression tests for the CSS bundle, local HTMX asset, GET fallback, status semantics, and external recipe selector.

### Information density

- Simplified Audit History explanatory copy.
- Reduced audit summary cards from four to three and removed the non-actionable retention card.
- Preserved tooltips and existing detailed audit data instead of adding permanent instructional panels.

## Verification Evidence

- Safe pytest: 28 passed.
- Release validator: PASS.
- Authenticated Audit History, filtered Audit History, and Recipes template renders: HTTP 200.
- Waitress HTTP probe: login, CSS bundle, and HTMX asset returned HTTP 200.
- Generated CSS bundle: 335,214 bytes, zero `@import` rules.
- No PLC connection, read, or write was performed.
- Chrome connector diagnostics passed, but its site policy rejected `http://127.0.0.1:5000`. Multi-resolution screenshots remain open until that local origin is allowed in the connector.

## Official Design Basis

- Google web.dev recommends avoiding CSS `@import` because it creates late-discovered render-blocking request chains.
- HTMX documents HTML-fragment enhancement, indicators, disabled controls, polling, local production hosting, and CSRF integration without requiring a SPA.
- IBM Carbon recommends table toolbars for search/filter/actions, compact density, sortable keyboard-accessible headers, and progressive disclosure.
- W3C WCAG 2.2 requires asynchronous status and error updates to be programmatically exposed without moving focus.

## Next Controlled Batches

1. Allow the CRS local origin in the Chrome connector and complete browser evidence at 1920x1080, 1366x768, tablet, and mobile widths.
2. Convert the audit endpoint to return a Jinja fragment for HTMX requests, reducing response bytes in addition to avoiding navigation.
3. Continue database portability through SQLAlchemy repositories and Alembic; do not claim MySQL runtime readiness before the shared behavioral suite passes.
4. Close plant-production gates: controlled live PLC evidence, backup/restore drill, HTTPS, Windows service supervision, log rotation, and real operator acceptance.

## Guardrails

- No partial PLC operations.
- No client-only authorization or validation.
- No CDN dependency at runtime.
- No decorative animation added to operational pages.
- Every enhanced operation keeps a normal server-rendered fallback.
