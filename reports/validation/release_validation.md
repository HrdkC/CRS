# CRS Release Validation

Status: **PASS**
Generated UTC: `2026-07-11T11:41:06+00:00`

| Check | Result | Detail |
|---|---:|---|
| Python compilation | PASS | compileall |
| SQLite integrity | PASS | ok |
| SQLite foreign keys | PASS | 0 violation(s) |
| CSS module imports | PASS | all imports resolve |
| CSS brace balance | PASS | balanced |
| Jinja template compilation | PASS | 0 error(s) |
| Literal template links | PASS | all literal links resolve |
| Unauthenticated GET smoke | PASS | 26 route(s), 0 server error(s) |
| Login page | PASS | 200 |
| CSRF rejection | PASS | 400 |
| Branded 404 | PASS | 404 |
| Security headers | PASS | required browser headers present |

Unauthenticated GET routes checked: 26.
No PLC connection, read, or write was performed.
Browser rendering is tracked separately because local browser access may be policy-blocked.
