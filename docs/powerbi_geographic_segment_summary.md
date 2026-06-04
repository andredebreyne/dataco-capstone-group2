# Power BI Geographic Segment Summary

Issue: `#145`

## Purpose

`powerbi_geographic_segment_summary` is a granular Power BI serving table designed to make the P04 geographic dashboard page responsive to the same slicers used across the AO1, AO2, and AO3 dashboard pages.

The existing `powerbi_geographic_summary` table remains useful for high-level geography-only visuals. However, it is aggregated independently at geography level and does not contain the segment, risk, profit-band, and date fields required for interactive filtering.

This table solves that modeling gap by keeping geography together with governed AO3 filter dimensions. A complementary enrichment job adds Power BI-friendly decision fields for better executive interpretation.

## Business Question

Which geographies remain exposed after filtering by operational priority segment, high-risk flag, expected-profit band, margin-policy tier, and time period?

## Why This Table Is Needed

The P04 page uses geographic visuals such as maps, treemaps, and country-level risk-margin scatter plots. The main dashboard slicers are usually sourced from `powerbi_ao3_order_segments` or related semantic-model dimensions.

Those slicers cannot reliably filter `powerbi_geographic_summary` because that table has a different grain and does not include:

- `ao3_priority_segment`
- `ao1_high_risk_flag`
- `ao2_expected_profit_band`
- compatible date keys

Forcing a direct relationship between different-grain tables in Power BI would create ambiguous or misleading filter behavior. The correct design is to create a serving table at a filter-compatible grain.

## Source Tables

| Source | Purpose |
| --- | --- |
| `ao3_risk_margin_segments` | Governed AO3 order-level risk, margin, and priority-segment outputs. |
| `dataco_customer_regional_features` | Customer, region, state, country, and coordinate fields used for map-ready geography. |

## Serving Grain

The table is aggregated by:

```text
country / region / state / rounded coordinates / order date keys / AO3 priority segment / AO1 high-risk flag / AO2 expected-profit band
```

This grain supports geography-level visuals while preserving the dashboard filters required for P04 interaction.

## Output Path

Default Delta output:

```text
/Volumes/workspace/default/raw_data/gold/powerbi_geographic_segment_summary
```

Default metadata outputs:

```text
models/dashboard/powerbi_geographic_segment_summary_metadata.json
models/dashboard/powerbi_geographic_decision_enrichment_metadata.json
models/dashboard/powerbi_geographic_segment_serving_metadata.json
```

## Scoped Workflow Integration

The PR includes a scoped Databricks workflow for P04:

```text
notebooks/pipeline/run_powerbi_geographic_segment_workflow.py
```

This workflow runs the full P04 geographic segment chain without requiring edits to the large monolithic project orchestrator:

```text
1. Build powerbi_geographic_segment_summary
2. Enrich it with serving-layer decision fields
3. Validate the output
4. Optionally export CSV fallback
5. Optionally register the Databricks SQL serving table
```

Workflow flags:

```python
RUN_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY = True
RUN_POWERBI_GEOGRAPHIC_DECISION_ENRICHMENT = True
RUN_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_VALIDATION = True
RUN_POWERBI_GEOGRAPHIC_SEGMENT_EXPORT = False
RUN_POWERBI_GEOGRAPHIC_SEGMENT_SERVING_REGISTRATION = False
```

Set the export and serving flags to `True` when the Delta output has been validated and the user wants to publish to local CSV or Databricks SQL.

## Power BI Serving Table

Recommended Databricks SQL table name:

```text
workspace.default.powerbi_geographic_segment_summary
```

Scoped registration script:

```text
src/dashboard/register_powerbi_geographic_segment_table.py
```

## CSV Fallback Export

Scoped CSV export script:

```text
src/dashboard/export_powerbi_geographic_segment_summary.py
```

Expected output:

```text
dashboard/exports/powerbi_geographic_segment_summary.csv
```

## Key Fields

| Field | Purpose |
| --- | --- |
| `map_location_country` | Country-level geography. |
| `map_location_region` | Region-level geography. |
| `map_location_state` | State-level geography. |
| `map_location_label` | Combined map label. |
| `map_latitude` | Rounded latitude for map visuals. |
| `map_longitude` | Rounded longitude for map visuals. |
| `geo_coordinates_available` | Coordinate availability flag. |
| `order_date_DateOrders` | Date field for the default Power BI relationship to `Dim_Date[Date]`. |
| `order_date_key` | Integer `yyyyMMdd` date key for optional DateKey-based models. |
| `order_week_key` | Week key for weekly trend or slicer support. |
| `order_month_key` | Month key for monthly trend or slicer support. |
| `ao3_priority_segment` | Governed AO3 segment for priority filtering. |
| `ao1_high_risk_flag` | Governed AO1 high-risk flag. |
| `ao2_expected_profit_band` | Display band derived from frozen AO2 predicted order profit. |
| `order_item_count` | Scored order-item count for the grain. |
| `high_risk_order_count` | High-risk order-item count for the grain. |
| `high_risk_order_rate` | High-risk count divided by order-item count. |
| `total_order_value` | Governed order value for the grain. |
| `total_predicted_profit` | Sum of frozen AO2 predicted profit for the grain. |
| `avg_ao3_predicted_margin` | Average predicted margin for the grain. |

## Power BI Display Fields

The enrichment job adds display labels and sort orders so Power BI visuals do not need ad hoc DAX formatting for common slicers.

| Field | Purpose |
| --- | --- |
| `ao3_priority_segment_label` | Business-facing AO3 segment label. |
| `ao3_priority_segment_sort_order` | Stable AO3 segment display order. |
| `ao1_high_risk_label` | Business-facing high-risk flag label. |
| `ao1_high_risk_sort_order` | Stable risk-label display order. |
| `ao2_expected_profit_band_sort_order` | Stable expected-profit band display order. |

## AO2 Expected-Profit Bands

The expected-profit band is a display-only derivative of frozen AO2 predicted profit:

```text
Negative Profit
$0 - $10
$10 - $25
$25 - $50
$50 - $100
$100+
```

It is designed for slicer interaction and should not be interpreted as a retrained profitability model or a revised AO3 policy.

## Margin Policy Tier

The enrichment job adds `ao2_margin_policy_tier` to improve visibility inside the dominant positive-margin population without changing the official AO3 cutoff.

Official AO3 still uses `0.0` as the profit/loss margin boundary. The margin-policy tier is a dashboard-serving interpretation layer:

```text
Loss or Negative Margin
Low Positive Margin
Core Positive Margin
Strategic Positive Margin
```

The positive tiers are based on the positive-margin distribution of the geographic serving table. This helps the dashboard answer whether a geography is merely profit-positive or strategically margin-attractive.

## Geographic Decision Enrichments

The enrichment job also adds geographic decision fields:

| Field | Purpose |
| --- | --- |
| `geo_data_quality_status` | Distinguishes complete coordinates, missing coordinates, and unknown geography. |
| `geo_exposure_tier` | Classifies geography by value exposure using total order value quantiles. |
| `geo_exposure_tier_sort_order` | Stable exposure tier display order. |
| `geo_risk_intensity_tier` | Classifies geography by high-risk order-rate quantiles. |
| `geo_risk_intensity_tier_sort_order` | Stable risk-intensity display order. |
| `geo_decision_archetype` | Executive decision profile combining segment, exposure, risk intensity, margin tier, and data quality. |
| `geo_decision_archetype_sort_order` | Stable archetype display order. |
| `geo_recommended_focus` | Short action label for executive tables and tooltip cards. |

Controlled archetypes:

```text
Priority Protection Geography
Selective Recovery Review
Preserve Service Geography
Standard Monitoring Geography
Operational Monitoring Geography
Data Quality Review
```

Recommended focus values are intended for visuals such as `Geographic Action Queue`, `Country Decision Portfolio`, and region-level treemaps.

## Recommended P04 Visual Usage

| Visual | Recommended source |
| --- | --- |
| High-level country map with no segment filtering | `powerbi_geographic_summary` or `powerbi_geographic_segment_summary` |
| Map responsive to AO3 segment slicer | `powerbi_geographic_segment_summary` |
| Treemap by region responsive to Priority Segment | `powerbi_geographic_segment_summary` |
| Country risk-margin scatter responsive to slicers | `powerbi_geographic_segment_summary` |
| Geographic action queue table | `powerbi_geographic_segment_summary` |
| Country or region decision archetype view | `powerbi_geographic_segment_summary` |
| Margin-policy sensitivity slicer | `powerbi_geographic_segment_summary` |

## Recommended Power BI Relationships

For the current dashboard model, use the date relationship below because
`Dim_Date[Date]` is a date column:

```text
powerbi_geographic_segment_summary[order_date_DateOrders]
  -> Dim_Date[Date]
```

If a future semantic-model version adds an integer date key to `Dim_Date`, the
integer relationship can be modeled instead:

```text
powerbi_geographic_segment_summary[order_date_key]
  -> Dim_Date[DateKey]
```

Avoid relating `order_date_key` directly to `Dim_Date[Date]` because those
columns use different data types.

## Governance Rules

- Do not force a direct Power BI relationship between different-grain tables.
- Do not expose target or realized-outcome columns.
- Do not retrain AO1 or AO2.
- Do not redefine AO3.
- Do not recalculate AO3 segment logic in Power BI.
- Treat margin-policy tier, decision archetype, and recommended focus as serving-layer enrichments, not new model outputs.
- Use this table as a serving artifact built from governed upstream outputs.

## Acceptance Checks

The validation script must confirm:

- all required geography, date, AO3, risk, profit-band, and enrichment columns exist;
- forbidden target/outcome fields are absent;
- filter dimensions are not null;
- controlled display and decision-enrichment values are valid;
- coordinates fall within valid latitude/longitude ranges;
- rates are between 0 and 1;
- metric counts are non-negative;
- build and enrichment metadata exists and references Issue `#145`.

## Dashboard Interpretation

This table enables the geographic dashboard to answer a more operationally useful question than the aggregate map alone:

> After the manager filters by segment, risk profile, profit band, margin-policy tier, or date period, where is the remaining geographic exposure concentrated?

This improves the P04 page from a static geographic overview into an interactive geographic decision-support layer.

Recommended executive takeaway for P04:

> Geographic exposure should be prioritized where risk, value, and margin-policy attractiveness overlap. The enriched serving table allows managers to distinguish priority protection geographies, selective recovery review geographies, preserve-service geographies, and data-quality review cases without changing the official AO3 model policy.
