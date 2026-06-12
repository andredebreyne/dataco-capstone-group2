# Power BI Country Label Standardization

Issue: `#59`

## Purpose

Power BI serving tables standardize `map_location_country` as English display labels for dashboard maps, slicers, and table visuals.

The source feature field `order_country_normalized` remains unchanged in the Silver/Gold analytical layers. Standardization is applied only when dashboard-ready fields are produced.

## Implementation

Country display labels are governed in:

```text
src/dashboard/country_label_standardization.py
```

The helper maps common Portuguese or ASCII-normalized country tokens, such as `franca`, `alemanha`, `reino_unido`, and `suecia`, to English labels such as `France`, `Germany`, `United Kingdom`, and `Sweden`.

Unknown country tokens are converted from underscore-separated tokens to readable title-case labels so the dashboard does not expose raw feature keys when a new country appears.

## Affected Power BI Serving Tables

The standardized label is applied to:

| Table | Field |
| --- | --- |
| `powerbi_geographic_summary` | `map_location_country` |
| `powerbi_geographic_segment_summary` | `map_location_country` |
| `powerbi_logistics_kpi_summary` | `map_location_country` |
| `powerbi_logistics_order_kpi_detail` | `map_location_country` |

## Validation

The related validation scripts assert that known Portuguese country labels are not present in `map_location_country` after the serving tables are generated.
