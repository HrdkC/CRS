# CRS Current Status

## Executive Summary

CRS is an advanced engineering release candidate, not yet a plant-production release. Core recipe, machine/stage configuration, phase master, PLC buffer, audit, user, import/export, and configuration-readiness workflows exist. The repository now has a non-mutating audit utility, safe release validator, generic workstation bootstrap, Waitress launcher, minimal health endpoints, and a small safe automated test suite.

No real PLC write was performed during this audit.

## Verified Baseline

| Area | Confirmed state |
|---|---|
| Flask routes | 111 statically inventoried declarations |
| Templates | 61 |
| CSS | 24 files, modular import structure |
| JavaScript | 1 shared file |
| SQLite schema | 40 tables, 16 indexes |
| Safe tests | 18 tests after the post-audit authorization fix |
| Password storage | Werkzeug password hashes |
| CSRF | Enabled and tested for rejection |
| Sessions | Server and client idle controls exist |
| Database | SQLite is the only complete runtime backend |
| SQLAlchemy | Partial use only; migration is incomplete |
| PLC | pycomm3 integration exists; no live call in this audit |
| Production server | Waitress launcher added; service installation not commissioned |
| PLC array route authorization | Engineering capability enforced and regression tested |

## Binding Recipe Rules

- Current RELEASED recipes may be edited only with old/new audit history.
- Historical released versions remain read-only.
- All active parameter values must validate before download.
- No partial PLC downloads are permitted.
- P15 First Stage: one phase group, 12 recipe rows, stage-specific exact PLC strings.
- P15 Second Stage: Cap Strip Side and B&T Side are recipe controlled. Shaping Side is fixed in PLC and excluded.

## Readiness Decision

Status: **CONDITIONAL RELEASE CANDIDATE**.

Suitable for continued offline engineering and controlled PLC trial. Not approved for unattended plant production until the P0 items in `CRS_GAP_ANALYSIS.md` are closed with evidence.
