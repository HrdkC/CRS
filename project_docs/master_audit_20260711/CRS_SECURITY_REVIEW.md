# CRS Security Review

## Scope

Review covered authentication, authorization indicators, sessions, CSRF, headers, SQL construction, file paths, dependency versions, network target input, secrets and exceptional conditions. This is an application review, not a penetration test.

## Confirmed Controls

- Passwords use Werkzeug hash generation and verification.
- SQL values reviewed are parameterized; no confirmed user-controlled SQL injection was found.
- CSRF protection rejects missing-token POST requests.
- Global session guard and role capability checks are present.
- Login attempt controls and audit events exist.
- Export paths are allowlisted by audit archive logic.
- Security headers now include CSP, frame denial, MIME protection, referrer policy, COOP and CORP.
- Production startup rejects the default secret, insecure cookies and missing trusted hosts.
- PLC addresses are syntactically validated and loopback/multicast/unspecified targets are rejected.
- Shared browser messages use `textContent` for external values.
- `pip-audit` reported no known vulnerabilities in the current requirements on 2026-07-11.

## Remaining Risks

- CSP still requires `unsafe-inline` because many templates contain inline code.
- Process-local login throttling is weaker with multiple workers.
- Security route inventory contains delegated wrappers requiring explicit role matrix tests.
- No independent DAST, SAST or penetration test has been completed.
- TLS, reverse-proxy trust and Windows service identity are deployment responsibilities.
- Dependency integrity is not hash-pinned and no SBOM is generated.

## Production Environment Minimum

```powershell
$env:CRS_DEPLOYMENT_MODE = "production"
$env:CRS_SECRET_KEY = "<random secret from approved secret store>"
$env:CRS_COOKIE_SECURE = "1"
$env:CRS_TRUSTED_HOSTS = "crs.plant.example,10.0.0.25"
$env:CRS_HOST = "127.0.0.1"
$env:CRS_PORT = "5000"
```

Do not store real secrets in source, batch files, screenshots or audit reasons. Align further verification with OWASP ASVS 5.0 and the OWASP Top 10 2025.

References: [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/), [OWASP Top 10](https://owasp.org/Top10/), [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), and [Flask web security](https://flask.palletsprojects.com/en/stable/web-security/).
