# Q02 AO2 Profitability Dashboard Page

Page: Power BI profitability view (AO2)

## Objective

This Power BI page answers the operational question:

> Where is profitability most exposed and which scored order items require
> margin-protection review?

The page presents governed AO2 outputs for executive prioritization. It does
not retrain AO2, reconstruct target or outcome fields, or calculate new model
predictions in Power BI.

## Audience and Decision

The primary audience is an operations leadership team reviewing predicted
profitability exposure. The page communicates:

- the held-out scored operational population;
- aggregate and average expected profit;
- aggregate expected margin;
- the distribution of frozen AO2 predicted-profit bands;
- model-validation evidence and limitations;
- the interaction between AO1 risk, AO2 margin, and AO3 prioritization; and
- the order items requiring margin-protection review.

## Governed Inputs

| Power BI table | Purpose |
| --- | --- |
| `powerbi_ao3_order_segments` | Primary held-out scored population with frozen AO1, AO2, and AO3 outputs. |
| `powerbi_ao2_evaluation_metrics` | Validation-only evidence for the selected AO2 candidate. |
| `Dashboard_AO2_Profit_Bands` | Stable display dimension for governed predicted-profit bands, including empty bands. |

## Validated Metrics

| Metric | Value |
| --- | ---: |
| Scored order items | `34,467` |
| Aggregate expected profit | `$740,319` |
| Average expected profit | `$21.48` |
| Aggregate expected margin | `10.4%` |
| Negative expected-profit items | `112` |
| Negative expected-profit rate | `0.3%` |
| AO2 validation rows | `28,883` |
| Validation RMSE | `$95.62` |
| Validation MAE | `$52.65` |
| Validation R2 | `0.012` |
| Wrong profit-sign share | `19.7%` |

The page presents AO2 as a prioritization signal, not as a precise item-level
financial forecast. Validation evidence and held-out operational exposure
metrics refer to different populations and remain explicitly labeled.

## Profit Bands

The semantic model derives stable display bands only from the frozen
`ao2_predicted_order_profit` output:

| Profit band | Scored order items |
| --- | ---: |
| `Negative Profit` | `112` |
| `$0 to $10` | `4,467` |
| `$10 to $25` | `18,565` |
| `$25 to $50` | `11,312` |
| `$50 to $100` | `11` |
| `$100+` | `0` |

The `$100+` band remains visible when empty so that the visual contract is
stable across refreshes.

## Page Storytelling and Business Interpretation

The AO2 Profitability page is designed as an economic exposure view. Its
purpose is not to provide precise item-level financial forecasting, but to
identify where expected profitability is concentrated, where margin pressure
appears, and which scored order items may require margin-protection review.

The page answers the business question in four steps:

1. **Define the scored profitability population.** The KPI strip begins with
   the same governed held-out scored population used across the dashboard. This
   keeps AO2 profitability analysis aligned with AO1 risk and AO3
   prioritization.
2. **Quantify expected economic exposure.** Aggregate expected profit, average
   expected profit, aggregate expected margin, and negative expected-profit
   items summarize the magnitude and direction of expected profitability. These
   metrics help leadership distinguish broad profitability exposure from a
   small number of negative-profit cases.
3. **Show where profitability is concentrated.** The profit-band distribution
   translates continuous AO2 predictions into stable executive bands. This
   makes it easier to identify whether most scored items sit near low-margin
   ranges or whether material exposure exists in negative or high-profit bands.
4. **Connect profitability to operational risk and prioritization.** The risk x
   margin scatter connects AO1 predicted late-delivery risk, AO2 predicted
   margin, and AO3 segment assignment. This shows whether profitability
   exposure is concentrated in high-risk or low-risk operating contexts.

The page therefore moves from profitability exposure to distribution, then to
validation evidence, and finally to an executive interpretation. The intended
decision is not to accept AO2 as a precise accounting forecast, but to use it
as a governed signal for economic triage.

## Visual Narrative

HTML Content (lite) visualization measures are stored in
`Dashboard_Visualizations` under:

```text
Q02 Where Is Profitability Most Exposed?
```

| Sequence | Visualization measure or native visual | Purpose |
| ---: | --- | --- |
| 1 | `Q02 | 01 Header` | Establish the AO2 operational context and governed-model status. |
| 2 | `Q02 | 02 KPI Profitability Strip` | Summarize predicted profitability exposure. |
| 3 | `Q02 | 03 Profit Band Distribution` | Show the stable frozen AO2 profit-band distribution. |
| 4 | `Q02 | 04 Validation Evidence` | Present validation metrics and concise metric definitions. |
| 5 | Native scatter: `Risk x Margin Exposure by AO3 Segment` | Connect AO1 risk, AO2 predicted margin, and AO3 prioritization. |
| 6 | `Q02 | 06 Methodology Note` | Separate validation evidence from held-out scored estimates. |
| 7 | `Q02 | 07 Executive Takeaway` | Close the page with the margin-protection interpretation. |

## Why These Visuals Were Used

| Visual | Rationale |
| --- | --- |
| Header | Establishes the AO2 page context, the profitability question, and the governed-output status before metrics are interpreted. |
| KPI Profitability Strip | Summarizes the economic exposure of the scored population using aggregate expected profit, average expected profit, aggregate margin, and negative expected-profit exposure. |
| Profit Band Distribution | Converts continuous predicted-profit values into stable executive bands so leaders can see where most order items are concentrated. |
| Validation Evidence | Shows AO2 model-performance limitations, including RMSE, MAE, R2, and wrong profit-sign share. This protects the interpretation by positioning AO2 as a triage signal rather than a precise financial forecast. |
| Risk x Margin Scatter | Connects AO1 risk, AO2 predicted margin, and AO3 prioritization in a single executive view. The intended design is one aggregated bubble per AO3 segment. |
| Methodology Note | Separates validation evidence from held-out scored estimates and reinforces that Power BI does not retrain AO2, reconstruct targets, or generate new predictions. |
| Executive Takeaway | Converts profitability evidence into a management interpretation focused on margin-protection review. |

## Interactive Filters

The AO1 and AO2 pages share synchronized slicers:

| Slicer | Field |
| --- | --- |
| Priority Segment | `powerbi_ao3_order_segments[ao3_priority_segment]` |
| Risk Classification | `powerbi_ao3_order_segments[ao1_high_risk_flag]` |
| Profit Band | `Dashboard_AO2_Profit_Bands[profit_band]` |
| Order Date | `powerbi_ao3_order_segments[order_date_DateOrders]` |

The header also includes a `Reset Filters` action to clear page selections.

## Native Scatter Contract

The native scatter chart uses explicit semantic-model measures to avoid
ambiguous implicit aggregations:

| Role | Field |
| --- | --- |
| X-axis | `[Average AO1 Risk for Scatter]` |
| Y-axis | `[Average Predicted Margin for Scatter]` |
| Size | `[Total Order Value for Scatter]` |
| Legend | `powerbi_ao3_order_segments[ao3_priority_segment]` |

Do not add `Order_Item_Id` to scatter details. The intended executive view is
one aggregated bubble per AO3 segment. Add a vertical reference line at `35%`
AO1 risk and a horizontal reference line at `0%` predicted margin.

The native scatter uses the governed AO3 segment field for grouping. A custom
display legend may be used for executive-readable segment labels when needed.

## Layout Standard

The page uses a `1920 x 1080` canvas, the shared dark executive operations
theme, and the P02 profitability wireframe:

| Visual | X | Y | Width | Height |
| --- | ---: | ---: | ---: | ---: |
| Header with synchronized slicers | `20` | `16` | `1880` | `190` |
| KPI strip | `20` | `218` | `1880` | `136` |
| Profit-band distribution | `20` | `366` | `940` | `336` |
| Validation evidence | `972` | `366` | `928` | `336` |
| Risk x margin scatter | `20` | `714` | `940` | `346` |
| Methodology note | `972` | `714` | `928` | `142` |
| Executive takeaway | `972` | `868` | `928` | `192` |

## Governance Rules

- AO2 predicted profit is frozen upstream.
- Profit bands are display-only derivatives of frozen AO2 predicted profit.
- Power BI does not retrain AO2 or reconstruct target or outcome fields.
- Validation evidence is not presented as realized financial performance.
- The scatter uses governed AO1, AO2, and AO3 outputs only.
- The page supports prioritization; it does not claim precise item-level
  forecasting.

## Review Evidence

For final review, attach a current screenshot of the Power BI page to the
dashboard evidence package and confirm:

- the synchronized slicers filter both AO1 and AO2 pages;
- `Reset Filters` clears the page selections;
- the profit-band distribution matches the validated band counts;
- the scatter renders one aggregated bubble per AO3 segment;
- all HTML visual components render without scrollbars; and
- the PBIP project has been saved before committing updated artifacts.
