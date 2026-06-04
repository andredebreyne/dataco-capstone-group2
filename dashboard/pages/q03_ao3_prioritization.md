# Q03 AO3 Operational Prioritization Dashboard Page

Issue: `[W7][P0][#4] Power BI: AO3 prioritization page #50`

## Objective

This Power BI page answers the operational question:

> Where should operations allocate attention first?

The page translates governed AO1 delivery-risk and AO2 profitability outputs
into differentiated AO3 operating treatments. It does not retrain models,
redefine thresholds, or claim realized intervention outcomes.

## Audience and Decision

The primary audience is supply-chain leadership allocating preventive capacity.
The page distinguishes:

- broad high-value orders requiring scalable preventive protection;
- financially fragile orders requiring selective expedite review;
- stable orders where service quality should be preserved without
  over-intervention; and
- routine orders that remain under the standard process.

## Governed Inputs

| Power BI table | Purpose |
| --- | --- |
| `powerbi_ao3_order_segments` | Held-out scored order-item population with frozen AO1, AO2, and AO3 outputs. |
| `powerbi_ao3_segment_summary` | Governed AO3 portfolio summary. |
| `powerbi_ao3_risk_margin_policy` | Frozen risk and margin cutoffs used by the deterministic AO3 matrix. |
| `powerbi_ao3_operational_recommendations` | Governed operating-treatment descriptions. |

## Validated Portfolio Metrics

| Metric | Value |
| --- | ---: |
| Scored order items | `34,467` |
| Active review queue | `13,804` |
| Protect high value at risk | `13,752` |
| Protected order value | `$2,816,571` |
| Expedite selectively | `52` |
| Preserve service | `20,603` |
| Standard process | `60` |
| Dashboard QA issue rows | `0` |

## Page Storytelling

The page turns model outputs into an operational allocation brief:

1. **Measure current workload.** The KPI strip separates active-review demand,
   scalable protection capacity, selective-expedite cases, and the stable
   service portfolio.
2. **Show recent operating pressure.** The weekly timeline compares protection
   workload with governed order value so leadership can distinguish volume
   growth from value intensity.
3. **Interpret the movement.** The operational brief explains why premium-cost
   actions should remain selective even when the broad preventive queue grows.
4. **Allocate capacity by treatment.** The action matrix assigns distinct
   handling rules to protect-first, selective-expedite, and preserve-service
   segments.

The intended decision is not to apply one blanket intervention. Leadership
should scale preventive controls for the broad protection queue, inspect the
selective-expedite queue item by item, and avoid unnecessary intervention cost
for the stable portfolio.

## Visual Narrative

HTML Content (lite) measures are stored in `Dashboard_Visualizations` under:

```text
Q03 V3 | Operational Decision Timeline
```

| Sequence | Visualization measure | Purpose |
| ---: | --- | --- |
| 1 | `Q03 V3 | 01 Decision Timeline Header` | Establish the AO3 operating-allocation question and governed-policy status. |
| 2 | `Q03 V3 | 02 Recent Performance KPI Strip` | Compare recent queue pressure and protected-value movement with the prior four weeks. |
| 3 | `Q03 V3 | 03 Weekly Capacity Timeline` | Show weekly protection workload and protected order value. |
| 4 | `Q03 V3 | 04 Operational Insight` | Translate recent portfolio movement into a managerial interpretation. |
| 5 | `Q03 V3 | 05 Action Matrix` | Define differentiated treatments for the AO3 queues. |

The complementary policy-explanation measures are stored under:

```text
Q03 Policy | Risk-Margin Strategy
```

These measures explain the frozen risk-margin quadrants for academic review
and governance traceability. They complement the operational timeline rather
than replace it.

## Interactive Filters

The AO3 page shares synchronized slicers with the AO1 and AO2 pages:

| Slicer | Field |
| --- | --- |
| Priority Segment | `powerbi_ao3_order_segments[ao3_priority_segment]` |
| High Delivery Risk | `powerbi_ao3_order_segments[ao1_high_risk_flag]` |
| Profit Band | `Dashboard_AO2_Profit_Bands[profit_band]` |
| Order Date | `powerbi_ao3_order_segments[order_date_DateOrders]` |

The page includes a `Reset Filters` action to clear page selections.

## Layout Standard

The page uses a `1920 x 1080` canvas and the shared dark executive operations
theme:

| Visual | X | Y | Width | Height |
| --- | ---: | ---: | ---: | ---: |
| Header with synchronized slicers | `20` | `16` | `1880` | `156` |
| Recent-performance KPI strip | `20` | `184` | `1880` | `132` |
| Weekly capacity timeline | `20` | `328` | `940` | `424` |
| Operational insight | `972` | `328` | `928` | `424` |
| Action matrix | `20` | `764` | `1880` | `296` |

## Governance Rules

- AO3 consumes frozen upstream AO1 and AO2 outputs.
- AO3 segment assignment is deterministic and uses governed policy cutoffs.
- Power BI does not retrain models, reconstruct targets, or redefine cutoffs.
- Protected value is governed order-value exposure, not realized savings.
- Selective-expedite items require individual review before premium-cost action.
- Dashboard outputs support prioritization; they do not claim intervention
  outcomes.

## Review Evidence

Before closing Issue `#50`, attach a final screenshot of the Power BI page to
the pull request and confirm:

- the synchronized slicers filter the AO3 page;
- `Reset Filters` clears the page selections;
- the AO3 segment counts match the validated portfolio metrics;
- the weekly timeline renders without scrollbars;
- the complementary policy page remains available for governance review; and
- the PBIP project has been saved before committing updated artifacts.
