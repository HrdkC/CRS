# CRS Official Research Register

Access date: 2026-07-11

Only official or primary documentation was used for release-candidate decisions. Guidance was adapted for an offline or plant-intranet industrial application; it was not copied blindly.

| Source | Organization | CRS applicability | Implemented or verified action | Deferred action and reason |
|---|---|---|---|---|
| [OWASP Top 10:2025](https://owasp.org/Top10/2025/0x00_2025-Introduction/) | OWASP | Broken access control, misconfiguration, supply chain, injection, authentication, logging and exceptional-condition handling | Backend role checks, production configuration gates, parameterized SQL review, dependency audit, security headers and branded error handling | Independent penetration testing and continuous monitoring require the commissioned plant environment |
| [OWASP ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/) | OWASP | Verification baseline for authentication, authorization, sessions, validation and audit controls | Safe security tests, CSRF rejection, direct-route permission review and security evidence pack | Full ASVS requirement-by-requirement certification remains a separate assurance exercise |
| [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) | OWASP | One-active-session rule, idle expiry, secure cookies, session lifecycle logging | Server/client timeout controls, session audit, production secure-cookie gate and active-session priority | Central session/throttle storage is required before multiple application workers are used |
| [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) | OWASP | Password handling, non-enumerating failures and login protection | Password hashes, controlled login messages, attempt audit and throttling | MFA and formal password reset are deferred until plant identity policy is approved |
| [File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) | OWASP | Excel import validation and storage boundaries | Extension/size checks, preview-before-commit workflow and controlled import directories | Malware scanning requires an approved offline scanner and operating procedure |
| [Flask Security Considerations](https://flask.palletsprojects.com/en/stable/web-security/) | Pallets | Resource limits, escaping, CSRF, CSP, cookies and browser headers | Upload limits, Jinja escaping, CSRF, CSP and secure response headers | CSP still permits inline code until remaining inline scripts/styles are externalized |
| [Flask Production Deployment](https://flask.palletsprojects.com/en/stable/deploying/) | Pallets | Development server must not be used for production | Waitress runner, startup check and activation-free Windows batch entry points | HTTPS reverse proxy and Windows service identity require site commissioning |
| [Flask ProxyFix](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/) | Pallets | Forwarded headers must only be trusted behind a known proxy count | Forwarded metadata is not blindly promoted to trusted client identity | ProxyFix remains disabled until the exact plant proxy chain is approved |
| [SQLAlchemy connection pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) | SQLAlchemy | Long-running central DB connections and transaction cleanup | SQLAlchemy use and health checks reviewed; release report identifies mixed DB access | Full repository migration from direct SQLite access is required before MySQL/MSSQL activation |
| [Alembic autogeneration](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) | Alembic | Controlled schema evolution and cross-database migration | Migration plan requires generated revisions to be reviewed and tested | Alembic lifecycle is deferred until all active tables/managers have SQLAlchemy metadata |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | W3C | Responsive layouts, focus, labels, target sizing and non-color status meaning | Skip link, visible focus, accessible labels, status text/icons and responsive navigation | Full WCAG AA claim requires real-browser and assistive-technology evidence |
| [Playwright accessibility testing](https://playwright.dev/docs/next/accessibility-testing) | Microsoft Playwright | Browser, responsive and automated accessibility checks | Browser test plan and required viewports are documented | Execution is blocked because the installed in-app browser plugin lacks its required client module; no unsupported workaround was used |

## Decision Summary

- CRS remains fail-closed for production secrets, secure cookies and trusted hosts.
- No ML result may authorize or write a PLC operation.
- No database switch is production-ready until SQLAlchemy/Alembic migration and parity testing are complete.
- No plant-production approval is valid without controlled live PLC, browser, backup-restore and HTTPS/service evidence.
