# CRS AI and Analytics Assessment

## Decision

Do not add an ML model to PLC download authorization or recipe validity. Deterministic limits, interlocks, identity checks, approvals and readback remain the safety authority.

## Useful Analytics Now

- Download success/failure rate by machine, stage and PLC revision.
- Parameter edit frequency and magnitude by recipe and source.
- Review/rejection cycle time.
- Repeated out-of-range or zero-value patterns.
- PLC communication duration and failure category trends.
- Template completeness and stale mapping reports.

These should use database aggregation and transparent filters before ML.

## Future ML Candidates

- Anomaly detection for unusual parameter combinations.
- Similar-recipe comparison and engineer review suggestions.
- Correlation between recipe changes and governed quality/defect outcomes.
- Predictive maintenance indicators from communication/error history.

## Data Required

- Stable machine/stage/program identity.
- Recipe and specification version lineage.
- Parameter values and engineering units.
- Download/readback outcome.
- Tire/SKU quality outcome with timestamps and traceable lot identity.
- Controlled missing-value and label definitions.

## Governance

Any model must be advisory, versioned, explainable, monitored for drift, and removable without affecting production. Predictions require user-visible confidence and evidence. No model should write PLC data or bypass approval/interlocks.
