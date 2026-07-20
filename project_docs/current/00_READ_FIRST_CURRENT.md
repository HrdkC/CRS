# CRS current-session entry point

Current release: **V11.11-RC1**.

Authoritative source rules:

1. Read this directory before changing architecture or safety behavior.
2. `CURRENT_RELEASE.md` states implemented hardening and remaining gates.
3. `AGREEMENT_DECISION_REGISTER.md` is the current decision register.
4. Older documents are historical and may be superseded.
5. Never run live PLC tools through ordinary pytest or CI.
6. Never include operational databases, secrets, backups or plant data in a release ZIP.
