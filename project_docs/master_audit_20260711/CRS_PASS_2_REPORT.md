# CRS Pass 2 Report

## Independent Re-Audit Scope

Pass 2 reran repository inventory, safe pytest, Python/template/CSS/link/route/database validation, startup import, bootstrap help, dependency audit and worktree review after all pass-one changes.

The post-audit refresh additionally ran a fresh isolated 53-step SQLite bootstrap twice and a real Waitress health/login probe on a spare loopback port. Both completed without changing the main database during the corrected isolation/probe runs.

## Shortfalls Found and Corrected

- The legacy P15 site migration was still available as a bootstrap option. It was removed from generic recovery because its historical group/count assumptions conflict with current P15 Second Stage rules.
- PLC registry addresses could reach ping/PLC paths without canonical validation. Central validation and safe form errors were added.
- Service diagnostics were missing. Minimal liveness/readiness endpoints were added without PLC access or sensitive details.
- Narrow navigation could wrap into unusable oversized buttons. A controlled accessible drawer was added.
- Validation and startup-check imports could run development compatibility synchronization. Check/test entry points now force startup migrations off.
- PLC array browsing and parameter creation exposed direct routes without their own engineering capability guard. All related routes now enforce `engineering_config`, and an OPERATOR regression test proves denial before manager access.

## Remaining Independent Findings

- SQLite remains embedded across active managers.
- CSP inline exceptions remain.
- Full authenticated role matrix and browser visual coverage remain incomplete.
- Live PLC and disaster-recovery acceptance evidence remains external to this code pass.

## Decision

Pass 2 confirms engineering release-candidate status. It does not upgrade the system to plant-production approved.

Database SHA-256 and modification time were unchanged across the final safe pytest, release validation and startup-check run.
