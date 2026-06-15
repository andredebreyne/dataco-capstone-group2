# Q05 Executive Command Center Dashboard Page

Issue: `[W7][P1][#6] Power BI: executive command center page`

## Objective

This Power BI page answers the executive question:

> Where should management act first across delivery risk, margin exposure, and
> operational prioritization?

The page consolidates AO1, AO2, AO3, and geographic insights into a single
management-facing command center. It is a decision-support overview and does
not replace the detailed AO1, AO2, AO3, or geographic pages.

## Audience and Decision

The primary audience is executive leadership reviewing the overall operating
picture. The page is designed to support:

- prioritization of active review queues;
- visibility into protected value at risk;
- selective-expedite governance;
- margin-protection awareness; and
- direction toward geographic follow-up when deployment choices are needed.

## Governed Inputs

| Power BI table | Purpose |
| --- | --- |
| `powerbi_ao3_order_segments` | Integrated AO1/AO2/AO3 held-out operational population. |
| `powerbi_geographic_summary` | Geographic deployment and hotspot context. |
| `Dashboard_AO2_Profit_Bands` | Stable profit-band slicer and distribution support. |
| `Dim_Date` | Official calendar dimension for date filtering and time-window analysis. |

## Page Storytelling

The command center provides the executive entry point:

1. **Start with business pressure.** KPI cards quantify active review demand,
   value to protect, expected profit, selective-expedite exposure, and
   negative-profit exposure.
2. **Explain recent movement.** Four-week movement cards compare current
   operating pressure with the prior four weeks.
3. **Translate into actions.** The management agenda separates protect-first,
   selective-expedite, and preserve-service actions.
4. **Point to deeper pages.** The page directs leaders to detailed AO1, AO2,
   AO3, and geographic pages when they need evidence or drill-down analysis.

## Visual Narrative

HTML Content (lite) measures are stored in `Dashboard_Visualizations` under:

```text
Q05 V2 | Executive Command Center
Q05 V2 | Executive Command Center | Large Type
```

| Sequence | Visualization measure | Purpose |
| ---: | --- | --- |
| 1 | `Q05 V2L | 01 Executive Command Header` | Establish the management action question and governed-data status. |
| 2 | `Q05 V2L | 02 Executive Business KPI Strip` | Summarize active review, protected value, profitability, expedite, and loss exposure. |
| 3 | `Q05 V2L | 03 Executive Movement Brief` | Compare latest four-week pressure with the prior four-week period. |
| 4 | `Q05 V2L | 04 Executive Action Agenda` | Translate the governed queues into executive action priorities. |
| 5 | `Q05 V2L | 05 Executive Geographic Direction` | Link the overview to the geographic hotspot page. |
| 6 | `Q05 V2L | 06 Weekly Protected Value Trend` | Show weekly protected-value movement as a business time-series visual. |

Large-type measures are preferred for the final executive page because they are
more legible in meeting-room presentation mode.

## Interactive Filters

The page should reuse the synchronized executive slicer pattern:

| Slicer | Field |
| --- | --- |
| Priority Segment | `powerbi_ao3_order_segments[ao3_priority_segment]` |
| High Delivery Risk | `powerbi_ao3_order_segments[ao1_high_risk_flag]` |
| Profit Band | `Dashboard_AO2_Profit_Bands[profit_band]` |
| Order Date | `Dim_Date[Date]` |

## Governance Rules

- Executive metrics reuse governed AO1, AO2, and AO3 outputs.
- The overview does not retrain models or recalculate thresholds.
- Four-week changes are operational comparisons, not statistical forecasts.
- Protected value is governed order-value exposure, not realized savings.
- Negative-profit exposure is modeled exposure, not realized loss.
- The page is intended for prioritization and navigation to deeper evidence.

## Review Evidence

For final review, attach a current screenshot of the Power BI page to the
dashboard evidence package and confirm:

- all KPI values match the detailed AO1, AO2, and AO3 pages;
- synchronized slicers work through `Dim_Date` and AO3 segment filters;
- large-type visuals render without scrollbars;
- the weekly protected-value trend is readable and not described as a forecast;
- the page clearly points executives toward the appropriate deeper lens; and
- the PBIP project has been saved before committing updated artifacts.
