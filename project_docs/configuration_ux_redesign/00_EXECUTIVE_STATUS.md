# Configuration UX redesign status

Release target: **CRS V13.1 Configuration Workflow**

The previous Configuration Readiness page exposed multiple technical domains on one long screen. V13.1 introduces a standard seven-step setup journey while preserving the existing engineering pages and managers.

Implemented:

- searchable Configuration Center with machine/stage cards;
- Start Setup and Resume Setup actions;
- persistent workflow/current-step/version tracking;
- live readiness-derived step states;
- Machine/Stage, PLC Assignment, PLC Tag Mapping, Parameter Template, Phase Controls, First Recipe, and Review steps;
- Standard journey separated from Engineering Tools;
- parameter-template source selection and read-only preview before commit;
- responsive light/dark workflow styling;
- migration, backfill, rollback, and focused safe tests.

External gates remain:

- supervised real PLC commissioning;
- production HTTPS and security-mode rollout;
- target-workstation browser acceptance and operator sign-off.

