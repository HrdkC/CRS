# MASTER CODEX PROMPT

## CRS Complete Status Audit, Gap Analysis, Modernization, Security Hardening, Browser Validation, AI/ML Analytics and One-File Deployment

You are acting as the **principal software architect, senior Flask/Python developer, industrial automation software engineer, database architect, UI/UX designer, cybersecurity reviewer, QA automation engineer, DevOps engineer and data analytics engineer** for this project.

The application is an industrial **Centralized Recipe System (CRS)** for PCR Tyre Building Machines. Treat it as a production-oriented industrial application in which database integrity, PLC safety, recipe traceability, authorization, auditability and reliable recovery are more important than visual appearance or development speed.

Your work must be based on the **actual repository currently opened in this Codex workspace**. Do not invent files, tables, models, routes, features, test results or completed functionality.

---

# 1. Primary Mission

Perform a complete review and controlled improvement of the entire CRS project.

You must:

1. Determine the current project status.
2. identify completed, partially completed, missing, duplicated, obsolete and unsafe functionality.
3. Compare the implementation with the project agreements in this prompt.
4. Research current official practices relevant to Flask, SQLAlchemy, Alembic, web application security, responsive UI, accessibility, browser automation, industrial auditability, database deployment and AI/ML analytics.
5. Create a prioritized gap analysis.
6. Modernize the complete GUI and user experience.
7. Harden authentication, authorization, sessions, concurrency, audit logging and configuration security.
8. Make the application responsive and usable on desktop, laptop, tablet and mobile screens.
9. Test every important route, button, form, permission rule, database operation and workflow through automated and manual browser inspection.
10. Perform the full review-and-improve process twice.
11. Produce clear evidence of what was inspected, modified, tested, passed, failed or deferred.
12. Make the application self-deployable through one controlled run/setup entry point.
13. Make future SQLite/MySQL/MSSQL configuration possible through a secure configuration mechanism without editing application source files.

Do not stop after preparing a report. Implement safe and justified improvements in the repository.

---

# 2. Mandatory Working Principles

## 2.1 Inspect before changing

Before editing any file:

* Read the repository instructions, project documentation, README files, project resume files, architecture documents and migration notes.
* Find the actual Flask application factory or startup path.
* Inventory all packages, blueprints, routes, models, templates, JavaScript files, CSS files, services, managers, PLC helpers, scripts and tests.
* Inspect the current database schema and migration mechanism.
* Inspect the current configuration and startup mechanism.
* Check Git status and current branch.
* Identify the latest real project baseline from the repository itself.
* Do not assume that an older file name or remembered baseline is still current.
* Preserve working behavior unless a verified defect or approved improvement requires modification.

Create a backup or work on a dedicated branch before broad changes.

## 2.2 No fake completion

Never report a feature as working only because code exists.

A feature is considered verified only when suitable evidence exists, such as:

* automated test result;
* browser interaction result;
* database assertion;
* route response verification;
* screenshot or trace;
* PLC simulator or explicitly approved test-tag validation;
* log or audit record verification.

Clearly distinguish:

* verified;
* implemented but not verified;
* partially implemented;
* missing;
* blocked by unavailable hardware or credentials;
* intentionally excluded.

## 2.3 Preserve industrial safety

Never write to real production PLC tags merely to test the application.

Use this order:

1. Existing simulator or mock PLC service.
2. Dedicated CRS test tags.
3. Offline fixtures.
4. Read-only checks.
5. Real PLC write tests only when an existing safe procedure and explicitly approved test environment are available.

Never weaken:

* manual-mode checks;
* download-enable checks;
* destination-buffer verification;
* recipe validation;
* checksum or fingerprint checking;
* read-back comparison;
* authorization;
* audit logging;
* operation locking;
* timeout handling;
* failure recovery.

Do not silently convert warnings into success.

---

# 3. Binding CRS Project Rules

Treat the following as mandatory unless the current repository contains a newer explicit project decision.

## 3.1 Technology and environment

* Backend: Python and Flask.
* ORM: SQLAlchemy.
* Development database: SQLite.
* Preferred production database: MySQL.
* Future database support: Microsoft SQL Server where practical.
* PLC communication: Allen-Bradley ControlLogix over Ethernet/IP, primarily through `pycomm3` or the established project communication layer.
* Deployment target: plant intranet.
* Application access: browser-based.
* Production configuration must not require editing Python source code.

## 3.2 Recipe-editing policy

* The current `RELEASED` recipe may be edited when the role is authorized.
* Every released-recipe value change must be audited.
* Historical recipe versions are locked and read-only.
* “Create Version” is primarily for significant revisions, major changes and trials.
* Unchanged values must not create false parameter-audit records.
* Change reason, user, role, source, old value, new value and timestamp must be recorded where required.

## 3.3 Roles and hierarchy

Use the established roles:

* `ADMIN`
* `ENGINEERING`
* `TECHNOLOGY`
* `PRODUCTION`
* `OPERATOR`
* `VIEWER`

Expected hierarchy:

`ADMIN > ENGINEERING > TECHNOLOGY > PRODUCTION > OPERATOR`

`VIEWER` is view-only.

Requirements:

* Backend authorization is mandatory for every protected operation.
* Hiding a menu or button is not sufficient authorization.
* Navigation, cards, actions and buttons must only be visible when useful to the current role.
* Direct URL access must also be rejected when unauthorized.
* Avoid scattered, inconsistent hard-coded role comparisons.
* Use a centralized permission or policy layer.
* Test a route-permission matrix for all roles.

## 3.4 Session rules

* One username may have only one active session.
* The existing active session has priority.
* A later login attempt must not automatically terminate the active session.
* The later attempt must be blocked and shown a professional “user already active” message with only appropriate workstation/session awareness metadata.
* The existing user should receive or see notification of the blocked attempt where the current architecture supports it.
* All roles, including `VIEWER`, follow the same session rule.
* Auto logout must be configurable by an authorized administrator.
* Auto-logout configuration belongs under Administration.
* A visible idle/session countdown should be available.
* The “settings saved” message must appear only after an actual successful save.
* Session activity, timeout, logout reason and blocked login attempts must be audited.
* Regenerate session identifiers at authentication and other privilege-boundary changes.
* Cookies must use secure production settings appropriate to HTTPS deployment.

## 3.5 Long-running operations and concurrency

Restore, Save, Download and Upload operations must:

* show an unmistakable operation-in-progress state;
* block duplicate submission;
* prevent accidental navigation where unsafe;
* disable incompatible actions until completion;
* expose clear progress where actual progress can be measured;
* return a clear success, warning or error result;
* release locks on success, expected failure, exception, timeout and application recovery;
* avoid permanent stale locks.

When one user is editing a recipe or executing a PLC operation, conflicting operations from other users must be safely blocked according to resource scope.

Do not rely only on an in-memory Python variable for production locking when multiple workers or processes may run.

Use a robust lock design supported by the selected deployment architecture, with:

* resource identifier;
* operation type;
* owner/session;
* acquisition time;
* heartbeat or lease;
* expiration;
* status;
* recovery process;
* audit trail.

## 3.6 Messages and visual status

Use consistent message semantics:

* Error: red, danger icon, clear corrective information.
* Warning: amber/yellow, warning icon.
* Success: green, confirmation icon.
* Information: blue or neutral information icon.

Do not communicate status through color alone. Include icon, text and accessible labels.

## 3.7 Client and audit metadata

Capture appropriate metadata such as:

* authenticated username;
* user ID;
* role;
* workstation or client identifier where reliably available;
* client IP;
* request host;
* user agent;
* trusted forwarded address where applicable;
* login source;
* operation source;
* timestamp;
* correlation/request ID;
* outcome and failure reason.

Do not blindly trust arbitrary proxy headers. Configure trusted proxies explicitly.

## 3.8 Audit retention and archive

* Retention rules must be configurable by an authorized role.
* Older audit/session records may be archived according to policy.
* Authorized administrators must be able to access archived historical records.
* Export must preserve traceability and use safe spreadsheet generation.
* Avoid spreadsheet-formula injection when exporting user-controlled values.
* Archive, restore, export and retention-setting changes must themselves be audited.

## 3.9 PLC recipe authority and identity

A recipe must not be trusted only by its recipe code.

Where applicable, verify recipe identity and authority using:

* recipe code;
* version;
* deterministic checksum or fingerprint;
* machine;
* stage;
* authority mode;
* parameter-definition compatibility;
* phase-control compatibility.

Do not overwrite local or CRS data merely because recipe codes appear equal.

## 3.10 Phase-control rules

### P15 First Stage

Preserve the verified phase-control data model and working restore behavior. Inspect actual master data, recipe mappings, validation and PLC buffer behavior before changing it.

### P15 Second Stage

The recipe-controlled phase groups are only:

* `CAP_STRIP_SIDE`
* `BT_SIDE`

`SHAPING_SIDE` is a fixed machine standard maintained in PLC logic and is not recipe data.

Therefore, do not:

* store `SHAPING_SIDE` as recipe data;
* expose it as an editable recipe field;
* import or export it as recipe data;
* include it in recipe validation;
* download it as recipe-controlled data;
* include it in recipe checksum as mutable recipe data.

The green/white/red status colors, AUTO START/AUTO STOP indications and other live SCADA/machine statuses are display state, not recipe data.

Do not add group mode, live color, auto status or timing to recipe storage unless the repository includes a newer approved requirement.

Preserve the verified behavior that restoring a recipe populates the correct CRS phase-control string buffer for both stages.

---

# 4. Initial Repository and System Inventory

Create a machine-readable and human-readable inventory covering:

* application entry points;
* Flask app factories;
* blueprints;
* route count;
* endpoint count;
* templates;
* CSS modules;
* JavaScript modules;
* ORM models;
* database tables;
* migrations;
* startup scripts;
* seed scripts;
* configuration files;
* services;
* background jobs;
* PLC communication modules;
* recipe managers;
* operation managers;
* authentication and session modules;
* authorization helpers;
* audit modules;
* export/import modules;
* tests;
* static assets;
* third-party dependencies;
* duplicated or dead files;
* local databases and backup files accidentally tracked;
* secrets or credentials accidentally stored in the repository.

Identify circular dependencies, oversized files, repeated logic and architectural boundaries that need improvement.

Check whether the CSS split/module architecture is clean and whether the import order preserves the intended cascade.

---

# 5. Status and Gap Report

Create a status report before major implementation.

For every significant subsystem, report:

* current status;
* evidence;
* gaps;
* risk;
* priority;
* recommended action;
* estimated implementation complexity;
* affected files;
* test method;
* final result after implementation.

At minimum cover:

1. Application structure.
2. Configuration management.
3. Database configuration.
4. Database schema and migrations.
5. Authentication.
6. Role-based access control.
7. Session management.
8. Concurrent-operation locking.
9. Audit logging.
10. Recipe lifecycle.
11. Released-recipe editing.
12. Historical-version protection.
13. Recipe parameter validation.
14. First-stage phase control.
15. Second-stage phase control.
16. PLC registry.
17. PLC read/write services.
18. Recipe restore.
19. Recipe save.
20. PLC download.
21. PLC upload.
22. Read-back verification.
23. Error and exception handling.
24. Dashboard.
25. Reports and visualization.
26. Search, filtering, sorting and pagination.
27. Responsive/mobile behavior.
28. Accessibility.
29. Browser compatibility.
30. Logging and diagnostics.
31. Backup and recovery.
32. Export/import safety.
33. Deployment.
34. Dependency and supply-chain security.
35. Test coverage.
36. Documentation.

Use priorities:

* `P0 – Safety/security/data-loss blocker`
* `P1 – Critical production gap`
* `P2 – Important reliability or usability gap`
* `P3 – Enhancement`
* `P4 – Optional future improvement`

Do not begin broad visual redesign until P0/P1 architecture or security defects that affect the redesign have been identified.

---

# 6. Internet Research Requirement

Research current practices using official or primary sources wherever possible.

At minimum review current guidance for:

* OWASP Top 10:2025;
* OWASP ASVS 5.x;
* OWASP authentication and session management guidance;
* OWASP secure design;
* OWASP logging and error handling;
* OWASP file upload and spreadsheet/export safety;
* Flask production deployment and web-security guidance;
* Flask `TRUSTED_HOSTS`;
* reverse-proxy and `ProxyFix` configuration;
* secure cookie settings;
* SQLAlchemy connection pooling and transaction handling;
* Alembic migrations and autogeneration review;
* MySQL secure deployment;
* Microsoft SQL Server connectivity where supported;
* Playwright browser automation;
* WCAG 2.2 accessibility principles;
* Bootstrap or the actual CSS framework used by the project;
* Python dependency auditing;
* secret management;
* secure headers;
* Content Security Policy;
* CSRF protection;
* rate limiting;
* structured logging;
* backup and recovery;
* AI/ML security when AI features are enabled.

Record:

* source title;
* source organization;
* access date;
* relevant requirement;
* applicability to CRS;
* implemented action;
* deferred action and reason.

Do not copy practices blindly. Adapt them to an offline or intranet industrial environment.

---

# 7. Modern UI and UX Modernization

Modernize the complete site into a coherent industrial web application.

## 7.1 Design system

Create or consolidate a reusable design system with:

* typography scale;
* spacing scale;
* responsive breakpoints;
* surface and border styles;
* consistent radii;
* shadows used sparingly;
* accessible color tokens;
* status colors;
* focus states;
* button sizes and variants;
* form controls;
* table patterns;
* cards;
* badges;
* chips;
* alerts;
* modal and drawer behavior;
* loading states;
* skeletons where useful;
* empty states;
* error states.

Avoid random page-specific CSS that causes inconsistent appearance.

## 7.2 Header and sidebar

Implement a professional application shell with:

* application logo and title;
* current machine/stage context where relevant;
* logged-in user icon/name/role;
* session countdown;
* notifications/status area;
* logout action;
* responsive navigation;
* proper icons with accessible labels.

Desktop sidebar requirements:

* expanded mode shows icon and label;
* collapsed mode shows icons only;
* icon tooltips appear in collapsed mode;
* active menu state is visible;
* section headings are clear;
* collapse state may be remembered safely;
* no menu item becomes unreadable or clipped.

Mobile navigation requirements:

* visible hamburger button;
* off-canvas or drawer navigation;
* correct focus handling;
* Escape-key support where applicable;
* backdrop and close control;
* no horizontal overflow;
* menu content remains scrollable;
* touch targets are appropriately sized.

## 7.3 Text, buttons and alignment

Inspect every page for:

* clipped labels;
* overflowing text;
* invisible text;
* low contrast;
* inconsistent capitalization;
* incorrect wrapping;
* buttons outside their containers;
* buttons with icons but no labels or tooltips;
* misaligned form fields;
* poorly centered actions;
* excessive centering that harms readability;
* inconsistent spacing;
* long table values without safe truncation or expansion.

Center text and buttons only where modern interface conventions support it, such as:

* login actions;
* empty states;
* confirmation dialogs;
* compact action cards;
* certain status cards.

Keep data tables, forms, audit details and long descriptions aligned for readability rather than blindly centering everything.

## 7.4 Forms

All forms must have:

* visible labels;
* required-field indication;
* accessible error text;
* retained safe values after validation errors;
* correct input types;
* help text where necessary;
* disabled/loading state;
* prevention of accidental repeated submission;
* clear save/cancel hierarchy;
* confirmation for high-impact actions;
* CSRF protection;
* server-side validation.

## 7.5 Tables

Modernize all tables with:

* responsive container;
* sticky header when useful;
* sortable columns where valid;
* server-side pagination for large datasets;
* search and filters;
* advanced filters collapsed by default where appropriate;
* filter chips showing active filters;
* reset filters;
* sensible default limits;
* column alignment based on data type;
* tooltip or expandable content for long text;
* accessible column headers;
* no unreadable mobile compression.

On narrow screens, choose the best pattern per table:

* horizontal scrolling;
* priority-column hiding;
* expandable rows;
* card representation.

Do not hide critical audit or safety data merely to fit mobile screens.

## 7.6 Login page

Create a professional login experience with:

* clear CRS identity;
* user icon;
* username and password fields;
* password visibility control;
* caps-lock awareness where practical;
* secure and non-enumerating failure messages;
* active-session-blocked message;
* workstation awareness details where allowed;
* loading state;
* accessible focus order;
* responsive layout;
* no exposed test credentials.

---

# 8. Modern Dashboard

Build a useful operational dashboard, not a decorative screen.

Display only authorized information.

Possible dashboard sections, based on available data:

* active machines;
* stage availability;
* recipe counts by state;
* recently modified recipes;
* current released recipe per machine/stage;
* last successful PLC download;
* last successful PLC upload;
* recent operation failures;
* parameter-validation results;
* recipe mismatch count;
* phase-control validation status;
* active users/sessions for authorized roles;
* lock status;
* audit activity;
* database health;
* PLC communication health;
* data freshness timestamp;
* system alerts;
* pending review/approval work where applicable.

Every KPI must define:

* source table/query;
* calculation;
* timeframe;
* refresh behavior;
* role visibility;
* empty-data behavior;
* timezone;
* last-updated timestamp.

Do not display fake values.

Use responsive cards and charts. Limit the first view to operationally meaningful information.

---

# 9. Data Visualization and AI/ML

## 9.1 Approved analytics tools

Use appropriate tools such as:

* NumPy;
* pandas;
* Matplotlib for offline/report generation;
* scikit-learn for justified machine-learning tasks;
* a browser charting library already approved or suitably lightweight for interactive visualization.

Do not make every page dependent on Python-generated static charts.

For responsive dashboard charts, prefer structured API data and responsive browser rendering unless server-generated reporting is specifically required.

## 9.2 Dynamic visualizations

Consider visualizations for:

* downloads/uploads over time;
* success/failure rates;
* parameter change frequency;
* recipe change activity;
* mismatch trends;
* operation duration;
* machine/stage comparison;
* user activity by permitted category;
* recurring validation failures;
* communication latency where recorded;
* audit-event distribution;
* recipe revision frequency.

Charts must include:

* title;
* units;
* timeframe;
* legend only when useful;
* accessible description;
* no-data state;
* role authorization;
* timezone and freshness;
* sensible aggregation;
* protection against unbounded queries.

## 9.3 AI/ML use cases

AI/ML must be optional, explainable and isolated from safety-critical control.

Evaluate whether sufficient historical data exists for:

* anomaly detection in parameter changes;
* unusual recipe-change frequency;
* repeated PLC mismatch patterns;
* abnormal operation durations;
* likely communication instability;
* unusual failed-login or blocked-session patterns;
* clustering recurring failure categories;
* trend forecasting for maintenance or operation workload.

Rules:

* Never allow ML output to write directly to PLCs.
* Never automatically change recipe values.
* Never bypass deterministic validation.
* Treat ML as advisory.
* Show confidence or anomaly score.
* Show the contributing signals where practical.
* Record model version, training period and feature definitions.
* Avoid personally invasive employee scoring.
* Detect data leakage.
* Use time-aware validation for chronological data.
* Do not claim prediction capability when data is insufficient.
* Provide a deterministic non-ML dashboard fallback.
* Make ML features disableable through configuration.
* Keep AI dependencies optional if they are not required for core CRS operation.

Before implementing a model, provide:

* business question;
* available dataset;
* row count;
* date range;
* target or anomaly definition;
* missing-data analysis;
* leakage analysis;
* baseline method;
* evaluation metric;
* expected operational action;
* limitations.

When data is insufficient, implement analytics-ready data collection and visualizations instead of pretending to build an accurate model.

---

# 10. Professional Security Hardening

Perform a security review aligned to current OWASP guidance.

## 10.1 Authentication

Check and improve:

* password hashing using an appropriate modern password hasher;
* password policy appropriate for plant use;
* default-password reset handling;
* inactive/locked users;
* failed-login handling;
* generic authentication errors;
* rate limiting or progressive throttling;
* password-change audit;
* session regeneration after login;
* secure password reset design if supported;
* no plaintext passwords in source, logs, database exports or setup scripts.

Do not introduce internet-dependent authentication into an isolated plant system unless explicitly required.

## 10.2 Authorization

* Deny by default.
* Validate authorization server-side.
* Centralize permission checks.
* Check object-level access, not only route access.
* Prevent numeric-ID enumeration from exposing unauthorized recipes, users, machines, audits or operations.
* Use opaque external identifiers where justified, but never treat obscurity as authorization.
* Test unauthorized GET, POST, PUT/PATCH and destructive actions.
* Prevent privilege escalation through modified form data or direct requests.

## 10.3 Sessions

Check:

* secure random session secrets;
* no hard-coded production secret;
* `HttpOnly`;
* `Secure` under HTTPS;
* appropriate `SameSite`;
* idle timeout;
* absolute timeout where required;
* session invalidation at logout;
* revoked/expired session enforcement;
* active-session priority rule;
* safe concurrency handling;
* stale-session cleanup;
* CSRF interaction;
* proxy and client-IP trust boundaries.

## 10.4 Input and output safety

* Validate all inputs server-side.
* Use ORM parameterization.
* Audit any raw SQL.
* Escape output by default.
* Review every `|safe` or equivalent bypass.
* Validate numeric ranges, enums, identifiers, dates and lengths.
* Validate uploaded/imported files by content and structure.
* Prevent path traversal.
* Prevent CSV/Excel formula injection.
* Limit request size and file size.
* Return safe user-facing errors.

## 10.5 CSRF, headers and browser security

Implement or verify:

* CSRF protection on state-changing browser requests;
* Content Security Policy suitable for the current asset strategy;
* `X-Content-Type-Options`;
* clickjacking protection through CSP `frame-ancestors` or appropriate header;
* referrer policy;
* permissions policy where appropriate;
* strict HTTPS behavior in production;
* HSTS only when HTTPS deployment is correctly established;
* trusted-host validation;
* no unnecessary wildcard origins;
* secure cache headers for sensitive pages.

Reduce or remove inline scripts/styles where they prevent a practical CSP.

## 10.6 Secrets and configuration

* No credentials in Git.
* No real secrets in sample configuration.
* `.env` or environment variables may be used for bootstrap secrets.
* Restrict configuration-page access to an authorized administrator.
* Encrypt stored database passwords using a server-held key not stored in the same database.
* Mask secrets after save.
* Never return stored passwords to the browser.
* Audit configuration changes without logging secret values.
* Validate database connections before activation.
* Preserve the previous valid configuration when a new configuration test fails.

## 10.7 Dependencies and supply chain

* Pin or constrain dependencies appropriately.
* Remove unused dependencies.
* Run vulnerability and outdated-package checks using suitable tools.
* Generate dependency inventory or SBOM where practical.
* Review third-party CDN use.
* Prefer locally hosted static assets for plant-intranet reliability and CSP simplicity.
* Verify licenses for introduced packages.
* Do not automatically apply breaking dependency upgrades without testing.

## 10.8 Logging and exceptional conditions

* Use structured logging.
* Add request/correlation IDs.
* Separate application, security, PLC and audit concerns appropriately.
* Do not log secrets, passwords, session tokens or full sensitive payloads.
* Include stack traces in server logs, not user responses.
* Provide consistent error pages.
* Handle database, PLC, timeout, validation and unexpected exceptions.
* Ensure failures do not leave a recipe, lock or operation in an ambiguous state.

---

# 11. Database Configuration Page

Implement a secure database configuration mechanism for future database changes.

## 11.1 Supported modes

At minimum account for:

* SQLite;
* MySQL;
* Microsoft SQL Server as a future or supported option according to installed drivers and repository architecture.

## 11.2 Configuration fields

Provide appropriate fields such as:

* database type;
* server/host;
* port;
* database name;
* username;
* password;
* driver where required;
* encryption/TLS mode;
* certificate verification option;
* connection timeout;
* pool size;
* pool recycle;
* optional instance or DSN for SQL Server;
* SQLite file path only when SQLite is selected.

Do not present irrelevant fields for the selected database type.

## 11.3 Required workflow

The configuration page must support:

1. Enter configuration.
2. Validate field format.
3. Test a temporary database connection.
4. Check server/database accessibility.
5. Check required privileges without destructive actions.
6. Save secrets securely.
7. Generate the runtime SQLAlchemy URL internally.
8. Run controlled migration readiness checks.
9. Show the migration plan.
10. Require explicit authorized activation.
11. Preserve the previous working configuration until activation succeeds.
12. Support rollback to the previous configuration.
13. Require application restart where architecture demands it.
14. Audit test, save, activation, failure and rollback without exposing credentials.

## 11.4 Bootstrap problem

Because the application database may not yet be configured, design a safe bootstrap mechanism.

Possible architecture:

* a small local bootstrap configuration store;
* environment-provided master encryption key;
* restricted setup mode accessible only locally or through a one-time bootstrap token;
* setup mode automatically disabled after successful configuration;
* separate production configuration from development defaults.

Do not place database credentials in the main application database in plaintext.

## 11.5 Migration requirements

Use Alembic or the established migration framework.

* `create_all()` may create a new schema but must not be treated as a replacement for upgrades.
* Review autogenerated migrations manually.
* Test migrations on a database copy.
* Back up before migration.
* Support migration status reporting.
* Make migrations repeatable and safe.
* Avoid destructive migration without explicit backup and confirmation.
* Test SQLite and MySQL differences.
* Keep SQL Server compatibility in mind where practical.

---

# 12. One-Run Setup and Self-Deployment

Create one primary startup/setup entry point suitable for Windows plant workstations.

Preferred result:

* `run_crs.bat` or a similarly clear primary Windows launcher;
* optionally a PowerShell implementation called by the launcher;
* a Python bootstrap module containing the actual portable logic.

The one-run workflow should:

1. Determine the project root safely.
2. Check supported Python version.
3. Create or reuse the virtual environment.
4. Install or verify pinned dependencies.
5. Install browser-test dependencies only when requested or required.
6. Create required directories.
7. Generate safe initial local configuration when absent.
8. Check secret-key requirements.
9. Validate database configuration.
10. Initialize a new database or apply pending migrations.
11. Seed only required baseline data.
12. Avoid duplicating seed rows on repeated runs.
13. Create the initial administrator through a secure interactive or one-time setup process.
14. Never hard-code a production password.
15. Check static assets.
16. Run a startup health check.
17. Start the production-appropriate WSGI server.
18. Write logs to a known location.
19. Show the local/intranet URL.
20. Exit clearly when a mandatory check fails.

The script must be idempotent. Running it again must not erase production data or recreate users.

Development and production modes must be explicit.

Do not use Flask’s development server as the recommended production service.

For Windows deployment, evaluate an appropriate production WSGI server and service wrapper compatible with the project. Document reverse-proxy and HTTPS options separately.

Provide:

* setup script;
* run script;
* migration command;
* health-check command;
* backup command;
* restore procedure;
* troubleshooting guide;
* clean uninstall guidance that does not delete data without explicit confirmation.

---

# 13. Browser Connector and Automated Browser Inspection

Use the browser automation or connector available in the environment.

Preferred order:

1. Existing Codex browser connector or approved MCP browser tool.
2. Playwright.
3. Selenium only when already established and Playwright is not practical.

Do not merely inspect HTML files. Start the actual application and interact with the rendered site.

## 13.1 Browser configuration

Configure browser tests for:

* Chromium or Microsoft Edge;
* Firefox;
* WebKit where supported;
* desktop 1920×1080;
* common laptop resolution;
* tablet portrait and landscape;
* representative mobile viewport;
* touch/mobile emulation;
* light mode;
* dark mode only if the application supports it;
* slow-network simulation for loading-state checks where practical.

Use test accounts for every role.

Never store production credentials in tests.

## 13.2 Test evidence

Enable useful evidence:

* screenshots on failure;
* browser trace on failure;
* console logs;
* failed network requests;
* page errors;
* HTML report;
* video only when useful and storage is controlled.

Check:

* browser console errors;
* JavaScript exceptions;
* failed static assets;
* broken images;
* missing icons;
* incorrect MIME types;
* 404/405/500 responses;
* CSP violations;
* accessibility findings;
* horizontal overflow;
* clipped elements;
* focus order;
* keyboard operation;
* mobile navigation.

## 13.3 Functional route and UI coverage

Test every meaningful route and action, including:

* login success;
* login failure;
* blocked second login;
* logout;
* idle timeout;
* role-based menus;
* direct unauthorized URL access;
* dashboard;
* machines;
* stages;
* PLC registry;
* recipe list;
* recipe view;
* recipe edit;
* released-recipe edit reason;
* unchanged-value behavior;
* historical-version lock;
* create version;
* restore;
* save;
* upload;
* download;
* operation locks;
* duplicate-click protection;
* audit history;
* filters;
* sorting;
* pagination;
* export;
* active sessions;
* auto-logout settings;
* database configuration;
* error pages;
* mobile menu;
* collapsed sidebar;
* responsive tables;
* validation errors;
* long labels and values;
* empty states.

Create route-discovery tooling so newly added routes are less likely to remain untested.

## 13.4 Visual inspection

Capture representative screenshots for all main pages and roles.

Review screenshots for:

* alignment;
* spacing;
* readability;
* contrast;
* consistent components;
* overlapping elements;
* hidden buttons;
* broken responsive layout;
* excessive whitespace;
* tiny touch targets;
* unclear active navigation;
* modal overflow;
* table readability.

Do not treat screenshot generation as proof of correct functionality. Pair visual evidence with assertions.

---

# 14. Complete Function-by-Function Review

Build an inventory of all project functions and methods.

Classify each one as:

* actively used;
* indirectly used;
* test-only;
* duplicate;
* dead code;
* deprecated;
* unsafe;
* too complex;
* missing validation;
* missing error handling;
* missing test;
* candidate for refactoring.

Run suitable static and dynamic checks:

* syntax compilation;
* import checks;
* linting;
* formatting check;
* type checking where practical;
* unit tests;
* integration tests;
* route tests;
* database tests;
* browser tests;
* security tests;
* dependency checks.

Focus special review on:

* transaction boundaries;
* broad exception handlers;
* swallowed exceptions;
* unsafe defaults;
* mutable global state;
* thread/process safety;
* raw SQL;
* string-built queries;
* file paths;
* temporary files;
* secret handling;
* session handling;
* role checking;
* JSON parsing;
* numeric conversion;
* PLC tag construction;
* array boundaries;
* timeout behavior;
* retry behavior;
* database rollback;
* lock cleanup;
* audit creation;
* exports;
* background workers.

Do not refactor stable industrial logic only for stylistic preference. Refactor when it improves correctness, maintainability, testability, security or verified usability.

---

# 15. Two-Pass Review and Improvement Cycle

You must execute the complete process twice.

## PASS 1 – Baseline Audit and Primary Remediation

1. Inventory repository.
2. Run baseline tests.
3. Start the application.
4. Inspect every main page and role.
5. Run browser tests.
6. Document baseline failures.
7. Create status and gap report.
8. Fix P0 and P1 issues first.
9. Implement justified P2 UI, reliability and deployment improvements.
10. Add or improve tests.
11. Run complete regression.
12. Record evidence.

## PASS 2 – Independent Re-Audit and Refinement

After Pass 1:

1. Treat the modified system as a new baseline.
2. Re-run repository inventory.
3. Re-run function and route discovery.
4. Re-run security review.
5. Re-run all role-permission tests.
6. Re-run desktop, tablet and mobile browser tests.
7. Re-check console, network and accessibility findings.
8. Re-check database migrations from a clean database.
9. Re-check upgrade using a copy of the existing database.
10. Re-check one-run deployment on a clean environment where practical.
11. Re-check operation locking and error recovery.
12. Re-check text clipping, button alignment, icons and responsiveness.
13. Find regressions introduced during Pass 1.
14. Fix justified findings.
15. Run the final regression suite.
16. Update final status and remaining-gap report.

The second pass must not simply repeat the first report. It must attempt to find new defects and regressions.

---

# 16. Testing Matrix

Create and execute a test matrix including:

## 16.1 Unit tests

* validators;
* permission rules;
* recipe identity/checksum;
* parameter normalization;
* phase-control logic;
* lock lifecycle;
* configuration parsing;
* database URL construction;
* dashboard calculations;
* audit formatting;
* export sanitization.

## 16.2 Integration tests

* authentication/session/database;
* recipe CRUD and lifecycle;
* released edit and audit;
* historical locking;
* PLC mock read/write;
* restore/save/upload/download flow;
* migration;
* configuration activation;
* archive/export;
* concurrency and stale-lock recovery.

## 16.3 Browser tests

* all main roles;
* desktop/mobile;
* all main workflows;
* error handling;
* accessibility checks;
* responsive layout;
* duplicate-click prevention;
* direct unauthorized access.

## 16.4 Security tests

* CSRF;
* access-control bypass;
* ID enumeration;
* forced browsing;
* session reuse;
* blocked active session;
* cookie flags;
* host-header handling;
* unsafe proxy headers;
* input injection;
* output escaping;
* export formula injection;
* path traversal;
* oversized request;
* sensitive-data exposure;
* security headers.

## 16.5 Database tests

* fresh SQLite setup;
* existing SQLite upgrade;
* MySQL connection configuration where available;
* MySQL clean migration where available;
* transaction rollback;
* connection failure;
* migration failure;
* backup and restore;
* repeated setup idempotency.

Never claim MySQL or SQL Server validation if those servers were unavailable. State exactly what was tested.

---

# 17. Performance and Responsiveness

Profile before optimizing.

Check:

* dashboard query count;
* N+1 queries;
* large unpaginated queries;
* repeated configuration/database reads;
* repeated PLC connection setup;
* blocking operations inside request handlers;
* large session payloads;
* oversized JavaScript/CSS;
* duplicate assets;
* chart payload size;
* audit-table query performance;
* missing indexes;
* database connection-pool settings;
* long-running export memory use.

Use:

* pagination;
* selective columns;
* appropriate indexes;
* caching only for non-safety-critical, properly invalidated data;
* asynchronous/background execution only where architecture safely supports it;
* polling intervals appropriate for plant resources;
* cancellation and timeout handling.

Do not introduce a distributed task queue unless the operational benefit justifies the additional deployment complexity.

---

# 18. Health, Diagnostics and Operations

Add or verify:

* application health endpoint;
* database health;
* migration status;
* PLC service health without unsafe writes;
* version/build information;
* configuration validation status;
* disk/log-directory status where practical;
* last successful scheduled/maintenance action;
* startup diagnostics;
* graceful shutdown;
* log rotation;
* backup status;
* alert for stale locks;
* alert for repeated operation failures.

Health endpoints must not expose secrets or excessive internal details to unauthorized users.

---

# 19. Documentation Deliverables

Create or update:

1. `CRS_CURRENT_STATUS.md`
2. `CRS_GAP_ANALYSIS.md`
3. `CRS_IMPROVEMENT_PLAN.md`
4. `CRS_SECURITY_REVIEW.md`
5. `CRS_UI_UX_REVIEW.md`
6. `CRS_BROWSER_TEST_REPORT.md`
7. `CRS_TEST_MATRIX.md`
8. `CRS_DATABASE_CONFIGURATION.md`
9. `CRS_DEPLOYMENT_GUIDE.md`
10. `CRS_BACKUP_RESTORE_GUIDE.md`
11. `CRS_AI_ANALYTICS_ASSESSMENT.md`
12. `CRS_PASS_1_REPORT.md`
13. `CRS_PASS_2_REPORT.md`
14. `CRS_FINAL_VALIDATION_REPORT.md`
15. `CRS_CHANGELOG.md`

Avoid duplicating the same long content across all files. Cross-reference where sensible.

---

# 20. Required Final Report Format

At completion, provide:

## A. Executive summary

* overall readiness;
* highest risks;
* most important improvements;
* whether production deployment is recommended.

## B. Baseline discovered

* actual branch;
* actual baseline/version;
* architecture;
* database;
* route/table/test counts;
* startup method.

## C. Status table

For every major subsystem:

* status before;
* changes;
* status after;
* evidence;
* remaining gaps.

## D. Security summary

* vulnerabilities found;
* severity;
* remediation;
* remaining risk;
* official guidance used.

## E. UI/UX summary

* pages redesigned;
* responsive behavior;
* accessibility findings;
* visual regressions fixed;
* screenshots/traces generated.

## F. Database summary

* configuration mechanism;
* supported engines;
* migration status;
* clean install result;
* upgrade result;
* rollback behavior.

## G. Browser-test summary

* browsers;
* viewports;
* roles;
* scenarios;
* pass/fail/skip count;
* unresolved failures.

## H. AI/analytics summary

* data availability;
* charts implemented;
* models implemented or rejected;
* evaluation evidence;
* safety limitations.

## I. Deployment summary

* one-run file;
* fresh setup result;
* repeat-run result;
* production WSGI method;
* health check.

## J. Pass comparison

* defects found in Pass 1;
* defects found only in Pass 2;
* regressions introduced and corrected;
* remaining unresolved items.

## K. Changed files

For each changed file:

* purpose;
* important changes;
* risk;
* tests.

## L. Commands executed

List the important commands actually executed.

## M. Final test results

Show actual outputs or concise summaries.

## N. Remaining work

List only genuine remaining gaps with reasons and priority.

---

# 21. Implementation Response Format

When communicating implementation work, use this structure:

**File → Code/Change → Where Applied → Run → Test → Expected Result → Actual Result**

For broad changes, group related files into a controlled change package.

Do not paste entire unchanged files unnecessarily.

---

# 22. Definition of Done

The task is complete only when:

* the real repository has been fully inventoried;
* status and gaps are documented;
* high-risk issues have been addressed or clearly blocked;
* the UI uses a consistent professional design system;
* the dashboard uses real data;
* navigation works in expanded, collapsed and mobile modes;
* important pages are responsive;
* text and buttons are visible and readable;
* backend permissions are tested for all roles;
* one-active-session behavior is tested;
* long-operation locking and cleanup are tested;
* recipe and phase-control rules are preserved;
* security checks are completed;
* migrations are validated;
* one-run setup is implemented and tested;
* browser automation is configured;
* major workflows are browser-tested;
* two complete review passes are performed;
* Pass 2 looks for regressions independently;
* tests and evidence are retained;
* remaining limitations are stated honestly.

---

# 23. Start Now

Begin with:

1. Reading repository instructions and project documentation.
2. Checking Git status and creating a safe working branch or backup.
3. Producing the repository inventory.
4. Running the baseline application and tests.
5. Identifying the actual database schema and current baseline.
6. Configuring the available browser connector or Playwright.
7. Producing the initial status and gap report.
8. Starting Pass 1 remediation by priority.

Do not ask for confirmation for routine safe inspection, testing, documentation or reversible improvements.

Do not perform destructive database operations or real production PLC writes.

Proceed systematically and preserve evidence for every conclusion.
