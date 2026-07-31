# Security review

- Existing `engineering_config` backend capability remains mandatory for every new route.
- All new POST routes use the existing global CSRF guard and `csrf_input()`.
- Workflow updates use `BEGIN IMMEDIATE` transactions and optimistic row versions.
- Parameter preview is read-only and creates no audit or domain rows.
- Parameter creation continues through the existing validated, audited, atomic service.
- No secret, SMTP, email, OTP, analytics, or external CDN dependency was added.
- No browser route can start PLC communication from the workflow itself.
- Existing PLC-live operations remain isolated in the durable worker and controlled by current authorization/interlock rules.

## Route and capability matrix

| Route | Method | Required backend capability | CSRF |
|---|---|---|---|
| `/configuration` | GET | `engineering_config` | n/a |
| `/configuration/<machine>/<stage>/setup` | GET | `engineering_config` | n/a |
| `/configuration/<machine>/<stage>/setup/progress` | POST | `engineering_config` | required |
| `/configuration/<machine>/<stage>/setup/review` | POST | `engineering_config` | required |
| `/parameters/setup-options/<machine>/<stage>` | GET/POST | `engineering_config` | required on POST |
| `/parameters/copy-template/<machine>/<stage>` | POST | `engineering_config` | required |

ADMIN and ENGINEERING retain the current configuration capability. TECHNOLOGY, PRODUCTION, OPERATOR, and VIEWER behavior remains governed by the existing central role map; the new routes do not add a parallel permission system.
