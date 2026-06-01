# Power BI Dashboard Wireframes

This folder contains versioned SVG page backgrounds for the DataCo executive
dashboard. Each Power BI page should be designed wireframe-first so that
semantic-model measures, HTML Content (lite) components, and native visuals
follow a deliberate executive narrative.

## Design Rules

- Use a `1920 x 1080` canvas with a `16:9` aspect ratio.
- Keep fixed visual structure in the SVG background.
- Keep titles, metrics, labels, and analytical conclusions dynamic in Power BI.
- Let HTML Content (lite) components render their own executive card surfaces.
- Keep the SVG background intentionally minimal so it does not duplicate HTML
  borders, radii, or panel fills.
- Use the shared palette from
  `dashboard/themes/dataco_executive_operations_dark.json`.
- Build each page from top to bottom and left to right: context, exposure,
  analysis, decision policy, evidence, and takeaway.

## Executive Visual Scale

Use a presentation-first scale for all dashboard pages. The dashboard must be
legible when presented on a meeting-room display or shared screen, not only
when edited at full zoom in Power BI Desktop.

| Token | Standard |
| --- | --- |
| Canvas | `1920 x 1080` |
| Outer margin | `20 px` |
| Primary gutter | `12 px` |
| Major section gap | `12 px` |
| Card radius | `12-14 px` |
| Card internal padding | `22-28 px` |
| Page title | `42-46 px`, weight `700` |
| Page subtitle | `20-22 px` |
| Section eyebrow | `17-19 px`, uppercase |
| KPI value | `46-50 px`, weight `700` |
| KPI label | `17-18 px`, uppercase |
| Panel title | `17-19 px`, uppercase |
| Panel body | `18-20 px`, line height `1.40-1.50` |
| Supporting note | `16-18 px`, line height `1.40-1.50` |

Use color and weight to establish hierarchy before increasing font size.
Executive pages should remain compact, but no decision-critical text should
render below `16 px`. When a panel cannot support this minimum, shorten its
copy or rebalance the grid before reducing the font size.

## Semantic-Model Organization

Keep semantic-model measures and HTML visualizations separate:

```text
Dashboard_Measures
Dashboard_Visualizations
```

Organize `Dashboard_Measures` by reusable analytical domain:

```text
Shared Operational KPIs
AO1 Delivery Risk
AO2 Profitability
AO3 Risk-Margin Prioritization
Governance QA
```

Organize `Dashboard_Visualizations` by stable business question rather than by
page number. Use a numbered prefix in each visualization measure name to define
its narrative order:

```text
Q01 Where Is Preventive Attention Required?
  Q01 | 01 Header
  Q01 | 02 KPI Exposure Strip
  Q01 | 03 Exposure Distribution
  Q01 | 04 Threshold Policy
  Q01 | 05 Confusion Matrix
  Q01 | 06 Methodology Note
  Q01 | 07 Executive Takeaway
```

This pattern keeps the field panel easy to scan while allowing a visualization
to be reused or repositioned without renaming nested display folders.

## P01 AO1 Delivery Risk

Background:

```text
dashboard/wireframes/p01_ao1_delivery_risk_background.svg
```

Business question:

```text
Which scored order items require preventive attention because of elevated
late-delivery risk?
```

| Slot | Coordinates | Recommended content |
| --- | --- | --- |
| Page header | `x=20, y=16, w=1880, h=158` | `Q01 | 01 Header` |
| KPI strip | `x=20, y=186, w=1880, h=136` | `Q01 | 02 KPI Exposure Strip` |
| Operational exposure | `x=20, y=334, w=1000, h=330` | `Q01 | 03 Exposure Distribution` |
| Decision policy | `x=1032, y=334, w=868, h=330` | `Q01 | 04 Threshold Policy` |
| Confusion matrix | `x=20, y=676, w=1000, h=384` | `Q01 | 05 Confusion Matrix` |
| Methodology note | `x=1032, y=676, w=868, h=150` | `Q01 | 06 Methodology Note` |
| Executive takeaway | `x=1032, y=838, w=868, h=222` | `Q01 | 07 Executive Takeaway` |

The executive takeaway closes the analytical reading path beside the confusion
matrix. The methodology note remains compact and sits directly above it.
The detailed threshold trade-off chart belongs on the governance page or in a
drill-through analytical view.
