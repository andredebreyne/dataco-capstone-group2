# Q04 Geographic and Commercial Hotspots Dashboard Page

Issue: `[W7][P1][#5] Power BI: geographic and commercial hotspots page`

## Objective

This Power BI page answers the operational question:

> Where should management deploy attention across markets, countries, and
> commercial hotspots?

The page extends the governed AO1, AO2, and AO3 outputs into a geographic
serving lens. It does not recreate model predictions, redefine thresholds, or
use realized intervention outcomes.

## Audience and Decision

The primary audience is supply-chain and commercial leadership deciding where
to focus operational review capacity. The page separates:

- large workload hotspots with high absolute item volume;
- severity hotspots with disproportionate high-risk rates;
- protected-value concentration by location; and
- selective-expedite exposure that may require local review.

## Governed Inputs

| Power BI table | Purpose |
| --- | --- |
| `powerbi_geographic_summary` | Governed geographic serving summary created from dashboard-safe outputs. |
| `powerbi_ao3_order_segments` | Held-out scored order-item population used for shared slicers and cross-page context. |
| `Dim_Date` | Official calendar dimension for date filtering and time-window analysis. |

## Page Storytelling

The page turns geographic summaries into an executive deployment lens:

1. **Define scope.** KPI cards show the active geographic footprint, order-item
   volume, high-risk exposure, and protected value.
2. **Separate scale from severity.** Ranking views distinguish locations with
   large operational workload from locations whose risk rate is unusually high.
3. **Support deployment choices.** Geographic visuals help leadership decide
   where to investigate routes, service partners, and operational capacity.
4. **Preserve governance.** The page uses governed summaries only and does not
   change AO1, AO2, or AO3 policy decisions.

## Visual Narrative

HTML Content (lite) measures are stored in `Dashboard_Visualizations` under:

```text
Q04 Geographic & Commercial Hotspots
```

| Sequence | Visualization measure | Purpose |
| ---: | --- | --- |
| 1 | `Q04 | 01 Geographic Hotspots Header` | Establish the location-deployment question and governed-output status. |
| 2 | `Q04 | 02 Geographic KPI Strip` | Summarize location count, countries, order items, high-risk exposure, and protected value. |
| 3 | `Q04 | 03 Volume Hotspot Ranking` | Rank high-volume operational hotspots by absolute high-risk workload. |
| 4 | `Q04 | 04 Severity Hotspot Ranking` | Rank high-severity locations where risk rate is disproportionate. |
| 5 | `Q04 | 05 Geographic Executive Takeaway` | Summarize the business interpretation and next review action. |

Native Power BI map and scatter visuals may complement the HTML measures when
coordinates are available and correctly categorized as non-summarized latitude
and longitude fields.

## Interactive Filters

The page should reuse the synchronized executive slicer pattern:

| Slicer | Field |
| --- | --- |
| Priority Segment | `powerbi_ao3_order_segments[ao3_priority_segment]` |
| High Delivery Risk | `powerbi_ao3_order_segments[ao1_high_risk_flag]` |
| Profit Band | `Dashboard_AO2_Profit_Bands[profit_band]` |
| Order Date | `Dim_Date[Date]` |

## Governance Rules

- Geographic outputs are a deployment lens, not a new model.
- Latitude and longitude must be used only as location attributes, not summed
  business metrics.
- Severity rankings should be interpreted with volume context.
- The page does not calculate final-test performance or realized savings.
- Dashboard outputs support prioritization and investigation, not causal claims.

## Review Evidence

For final review, attach a current screenshot of the Power BI page to the
dashboard evidence package and confirm:

- slicers filter the geographic visuals consistently;
- location fields render with the expected data categories;
- geographic summaries match the governed serving-layer table;
- map/scatter visuals do not aggregate latitude or longitude as business KPIs;
- the page distinguishes volume hotspots from severity hotspots; and
- the PBIP project has been saved before committing updated artifacts.
