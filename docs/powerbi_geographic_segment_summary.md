# Power BI Geographic Segment Summary

Issue: `#145`

## Purpose

`powerbi_geographic_segment_summary` is a granular Power BI serving table designed to make the P04 geographic dashboard page responsive to the same slicers used across the AO1, AO2, and AO3 dashboard pages.

The existing `powerbi_geographic_summary` table remains useful for high-level geography-only visuals. However, it is aggregated independently at geography level and does not contain the segment, risk, profit-band, and date fields required for interactive filtering.

This table solves that modeling gap by keeping geography together with governed AO3 filter dimensions.

## Business Question

Which geographies remain exposed after filtering by operational priority segment, high-risk flag, expected-profit band, and time period?

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

Default metadata output:

```text
models/dashboard/powerbi_geographic_segment_summary_metadata.json
```

## Power BI Serving Table

Recommended Databricks SQL table name:

```text
workspace.default.powerbi_geographic_segment_summary
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
| `order_date_key` | Integer date key for date filtering. |
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

## Recommended P04 Visual Usage

| Visual | Recommended source |
| --- | --- |
| High-level country map with no segment filtering | `powerbi_geographic_summary` or `powerbi_geographic_segment_summary` |
| Map responsive to AO3 segment slicer | `powerbi_geographic_segment_summary` |
| Treemap by region responsive to Priority Segment | `powerbi_geographic_segment_summary` |
| Country risk-margin scatter responsive to slicers | `powerbi_geographic_segment_summary` |
| Geographic action queue table | `powerbi_geographic_segment_summary` |

## Governance Rules

- Do not force a direct Power BI relationship between different-grain tables.
- Do not expose target or realized-outcome columns.
- Do not retrain AO1 or AO2.
- Do not redefine AO3.
- Do not recalculate AO3 segment logic in Power BI.
- Use this table as a serving artifact built from governed upstream outputs.

## Acceptance Checks

The validation script must confirm:

- all required geography, date, AO3, risk, and profit-band columns exist;
- forbidden target/outcome fields are absent;
- filter dimensions are not null;
- coordinates fall within valid latitude/longitude ranges;
- rates are between 0 and 1;
- metric counts are non-negative;
- metadata exists and references Issue `#145`.

## Dashboard Interpretation

This table enables the geographic dashboard to answer a more operationally useful question than the aggregate map alone:

> After the manager filters by segment, risk profile, profit band, or date period, where is the remaining geographic exposure concentrated?

This improves the P04 page from a static geographic overview into an interactive geographic decision-support layer.
