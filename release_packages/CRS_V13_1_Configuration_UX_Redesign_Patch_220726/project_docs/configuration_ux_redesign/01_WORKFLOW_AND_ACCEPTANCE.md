# Guided configuration workflow

| Step | Completion source | Primary action |
|---|---|---|
| 1. Machine and Stage | active machine/stage records | Confirm target |
| 2. PLC Assignment | active PLC assigned to stage | Save PLC Assignment |
| 3. PLC Tag Mapping | all required stage tag purposes valid | Map Tag |
| 4. Parameter Template | Used rows exist and pass index/limit validation | Preview Template Rows |
| 5. Phase Controls | required stage groups and choices exist | Configure Phase Controls |
| 6. First Recipe | at least one non-test recipe exists | Create First Recipe |
| 7. Review and Readiness | no blocking readiness checks | Save Review Evidence |

Statuses are `NOT_STARTED`, `IN_PROGRESS`, `NEEDS_ATTENTION`, `BLOCKED`, `COMPLETE`, `OPTIONAL`, and `NOT_APPLICABLE`. Displayed status is derived from current readiness checks. The database stores current position, last viewer, completion evidence, timestamps, and row versions.

P15 Second Stage acceptance remains selection-only for `CAP_STRIP_SIDE` and `BT_SIDE`. `SHAPING_SIDE`, stop, and position are not created, edited, validated, counted, imported, exported, restored, or downloaded as recipe data.

Accessibility acceptance:

- semantic navigation and progressbar roles;
- visible current step and text status, not color alone;
- keyboard-accessible links, forms, and buttons;
- responsive layouts down to 390 x 844;
- readable light and dark surfaces;
- no internal horizontal page overflow.

