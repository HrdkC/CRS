# CRS Changelog

## 2026-07-12 Progressive UI and Asset Delivery

- Replaced the browser CSS `@import` chain with a generated single-file production bundle while retaining modular source CSS.
- Added bundle creation to workstation setup and stale-bundle detection to release validation.
- Added locally hosted, integrity-verified HTMX 2.0.10 for progressive server-rendered interactions.
- Modernized Audit History filtering and server sorting to update in place with accessible status feedback and normal GET fallback.
- Externalized base theme bootstrap and recipe machine/stage selector JavaScript.
- Reduced persistent Audit History explanation text and removed one non-actionable summary card.
- Added safe progressive UI regression tests and implementation documentation.
- Browser screenshots remain pending because the browser runtime was unavailable; no PLC call was performed.

## 2026-07-11 Post-Audit Authorization and Evidence Refresh

- Enforced `engineering_config` on PLC array browser, parameter-from-array and next-available-index routes.
- Added a direct route-handler regression test proving OPERATOR denial.
- Refreshed safe validation to 18 passing tests.
- Added the official research register and updated the current browser-plugin blocker.

## 2026-07-11 Master Prompt Pass

### Added

- Repository audit tool and reports.
- Release validation tool and reports.
- Waitress launcher plus setup/run batch files.
- Safe bootstrap, security, health and PLC input tests.
- Liveness and readiness routes.
- Responsive navigation drawer.
- Complete two-pass audit documentation pack.

### Changed

- Bootstrap help is non-mutating and machine-specific data migrations are excluded.
- Bootstrap optional failures cannot report success.
- Production startup enforces secret, secure cookies and trusted hosts.
- Security middleware initialization fails closed.
- Browser security headers expanded.
- Shared JavaScript no longer inserts external alert text as HTML.
- PLC addresses are canonicalized and unsafe targets rejected.
- Waitress added to runtime requirements.

### Safety Notes

- No real PLC operation was executed.
- No production database was deleted or reset.
- A pre-change local backup exists at `_local_backups/master_prompt_full_audit_20260711_121916`.
