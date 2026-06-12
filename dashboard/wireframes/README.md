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

## Continuation Convention

Use the following structure for every new executive dashboard page:

```text
dashboard/
  pages/
    qNN_<analytical_domain>.md
  themes/
    dataco_executive_operations_dark.json
  wireframes/
    pNN_<analytical_domain>_background.svg
```

Use `QNN` for the stable business-question sequence and `PNN` for the physical
Power BI page sequence. Keep these identifiers aligned whenever one page
answers one business question:

```text
Q01 / P01  AO1 delivery risk
Q02 / P02  AO2 profitability
Q03 / P03  AO3 risk-margin prioritization
Q04 / P04  geographic and commercial hotspots
Q05 / P05  executive command center
```

Create visualization measures in `Dashboard_Visualizations` with this pattern:

```text
QNN | 01 Header
QNN | 02 KPI Strip
QNN | 03 Primary Analysis
QNN | 04 Decision Policy
QNN | 05 Supporting Evidence
QNN | 06 Methodology Note
QNN | 07 Executive Takeaway
```

Adjust the descriptive suffix when the analytical content requires it, but
preserve the numbered storytelling order. Store reusable metric measures in
`Dashboard_Measures` under the corresponding analytical-domain folder.

## HTML Content Lite Root

Every HTML Content (lite) visualization must use an overflow-safe root
container. This avoids scrollbars introduced by the visual host while
preserving presentation-scale typography:

```html
<div style="position:absolute;inset:2px;overflow:hidden;box-sizing:border-box;">
  ...
</div>
```

Reduce internal padding, gaps, or visible copy before reducing font size. Do
not allow decision-critical text below `16 px`.

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

## P02 AO2 Profitability

Background:

```text
dashboard/wireframes/p02_ao2_profitability_background.svg
```

Business question:

```text
Where is profitability most exposed and which scored order items require
margin-protection review?
```

| Slot | Coordinates | Recommended content |
| --- | --- | --- |
| Page header with synchronized slicers | `x=20, y=16, w=1880, h=190` | `Q02 | 01 Header` plus Power BI slicers |
| KPI strip | `x=20, y=218, w=1880, h=136` | `Q02 | 02 KPI Profitability Strip` |
| Profit-band distribution | `x=20, y=366, w=940, h=336` | `Q02 | 03 Profit Band Distribution` |
| Validation evidence | `x=972, y=366, w=928, h=336` | `Q02 | 04 Validation Evidence` |
| Risk x margin scatter | `x=20, y=714, w=940, h=346` | Native Power BI scatter chart |
| Methodology note | `x=972, y=714, w=928, h=142` | `Q02 | 06 Methodology Note` |
| Executive takeaway | `x=972, y=868, w=928, h=192` | `Q02 | 07 Executive Takeaway` |

The AO2 page combines premium HTML summary surfaces with one native scatter
chart. The scatter preserves executive interactivity while the HTML profit-band
distribution maintains the visual language established on P01.

## P04 Geographic and Commercial Hotspots

Business question:

```text
Where should management deploy attention across markets, countries, and
commercial hotspots?
```

Recommended structure:

| Slot | Recommended content |
| --- | --- |
| Page header with synchronized slicers | `Q04 | 01 Geographic Hotspots Header` plus Power BI slicers |
| Geographic KPI strip | `Q04 | 02 Geographic KPI Strip` |
| Volume hotspot ranking | `Q04 | 03 Volume Hotspot Ranking` |
| Severity hotspot ranking | `Q04 | 04 Severity Hotspot Ranking` |
| Geographic map or scatter | Native Power BI visual using governed geographic summary fields |
| Executive takeaway | `Q04 | 05 Geographic Executive Takeaway` |

Use geography as a deployment lens. Do not sum latitude or longitude as
business metrics, and do not allow geographic summaries to redefine AO1, AO2,
or AO3 decisions.

## P05 Executive Command Center

Business question:

```text
Where should management act first across delivery risk, margin exposure, and
operational prioritization?
```

Recommended structure:

| Slot | Recommended content |
| --- | --- |
| Page header with synchronized slicers | `Q05 V2L | 01 Executive Command Header` plus Power BI slicers |
| Executive KPI strip | `Q05 V2L | 02 Executive Business KPI Strip` |
| Recent movement brief | `Q05 V2L | 03 Executive Movement Brief` |
| Management action agenda | `Q05 V2L | 04 Executive Action Agenda` |
| Geographic direction | `Q05 V2L | 05 Executive Geographic Direction` |
| Weekly protected-value trend | `Q05 V2L | 06 Weekly Protected Value Trend` |

Prefer the large-type `Q05 V2L` measures for final presentation. The command
center should summarize the operating picture and direct executives to the
detailed AO1, AO2, AO3, and geographic pages for deeper evidence.
