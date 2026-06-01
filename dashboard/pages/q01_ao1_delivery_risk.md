# Q01 AO1 Delivery Risk Dashboard Page

Issue: `[W7][P0][#2] Power BI: delivery risk page (AO1) #48`

## Objective

This Power BI page answers the operational question:

> Which scored order items require preventive attention because of elevated
> late-delivery risk?

The page presents governed AO1 outputs for executive decision support before
dispatch. It does not retrain the AO1 model, reconstruct target labels, or
recalculate the approved risk threshold.

## Audience and Decision

The primary audience is an operations leadership team reviewing where
preventive attention is required. The page is designed to communicate:

- the size of the held-out scored operational population;
- the number and share of order items flagged as high risk;
- the approved AO1 operating threshold;
- the validation trade-offs associated with that threshold;
- the validation confusion matrix; and
- a concise executive takeaway.

## Governed Inputs

| Power BI table | Purpose |
| --- | --- |
| `powerbi_ao3_order_segments` | Primary held-out scored population with frozen AO1 probabilities and risk flags. |
| `powerbi_ao1_decision_threshold_policy` | Approved AO1 threshold and validation-policy metrics. |

The page consumes upstream governed outputs. Power BI must not derive a new
threshold or alter the `ao1_high_risk_flag`.

## Validated Metrics

| Metric | Value |
| --- | ---: |
| Scored order items | `34,467` |
| High-risk order items | `13,804` |
| High-risk rate | `40.0%` |
| Average late-delivery risk | `52.4%` |
| Approved AO1 threshold | `35.0%` |
| Validation rows | `27,643` |
| Validation recall | `61.7%` |
| Validation precision | `84.7%` |
| Validation alert rate | `41.5%` |
| True positives | `9,726` |
| False positives | `1,758` |
| False negatives | `6,035` |
| True negatives | `10,124` |

Validation metrics and operational exposure metrics refer to different
populations and remain explicitly labeled on the page.

## Page Storytelling and Business Interpretation

The AO1 Delivery Risk page is designed as a preventive operations view. Its
purpose is not to explain historical delivery failure after the fact, but to
identify which scored order items should receive operational attention before
dispatch.

The page answers the business question in four steps:

1. **Define the operational population.** The KPI strip starts by showing the
   total number of scored order items included in the governed held-out
   population. This establishes the denominator used by the page and avoids
   mixing validation metrics with operational exposure metrics.
2. **Quantify current risk exposure.** The high-risk count, high-risk rate,
   and average late-delivery risk show how much of the scored population is
   exposed to elevated delivery risk. These metrics allow operations leaders
   to understand whether the alert population is small, moderate, or material
   enough to require active triage.
3. **Connect exposure to the approved decision policy.** The threshold policy
   panel separates descriptive exposure from the governed decision rule. The
   `35.0%` threshold is not recalculated in Power BI. It is reused from the
   upstream AO1 decision policy so that the dashboard remains a consumption
   layer, not a modeling layer.
4. **Validate the decision rule before recommending action.** The confusion
   matrix and validation trade-offs show how the selected threshold performed
   on the validation population. This is important because a high-risk flag is
   only useful if leadership understands the balance between captured
   late-delivery cases and unnecessary alerts.

The page therefore moves from operational exposure to decision policy, then to
validation evidence, and finally to an executive takeaway. This sequence
supports a practical decision: which order items should be reviewed first for
preventive attention.

## Visual Narrative

The page uses seven HTML Content (lite) visualization measures stored in
`Dashboard_Visualizations` under:

```text
Q01 Where Is Preventive Attention Required?
```

| Sequence | Visualization measure | Purpose |
| ---: | --- | --- |
| 1 | `Q01 | 01 Header` | Establish the AO1 operational context and policy status. |
| 2 | `Q01 | 02 KPI Exposure Strip` | Summarize the primary decision metrics. |
| 3 | `Q01 | 03 Exposure Distribution` | Compare flagged and below-threshold scored order items. |
| 4 | `Q01 | 04 Threshold Policy` | Present the frozen threshold and validation trade-offs. |
| 5 | `Q01 | 05 Confusion Matrix` | Show validation outcomes at the approved threshold. |
| 6 | `Q01 | 06 Methodology Note` | Separate validation evidence from held-out scored exposure. |
| 7 | `Q01 | 07 Executive Takeaway` | Close the page with the business interpretation. |

## Why These Visuals Were Used

| Visual | Rationale |
| --- | --- |
| Header | Establishes the page context, the AO1 decision objective, and the governed-policy status before any metric is interpreted. |
| KPI Exposure Strip | Summarizes the operational scale of the problem by showing scored order items, high-risk items, high-risk rate, average late-delivery risk, and the approved threshold context. |
| Exposure Distribution | Shows how the scored population is split between order items above and below the frozen AO1 threshold. This makes the alert population visually interpretable. |
| Threshold Policy | Explains the decision rule used to classify order items as high risk. The threshold is shown separately from descriptive KPIs to emphasize that it is a governed upstream policy, not an interactive dashboard assumption. |
| Confusion Matrix | Provides validation evidence for the selected threshold. It shows true positives, false positives, false negatives, and true negatives so reviewers can evaluate the operational trade-off between missed late deliveries and unnecessary alerts. |
| Methodology Note | Prevents misinterpretation by separating validation evidence from held-out operational scoring. It also states that Power BI does not retrain the model, reconstruct targets, or redefine the alert policy. |
| Executive Takeaway | Converts the analytical evidence into a concise management interpretation focused on preventive operational attention. |

## Layout Standard

The page uses a `1920 x 1080` canvas and the dark executive operations theme.
The current layout coordinates are:

| Visual | X | Y | Width | Height |
| --- | ---: | ---: | ---: | ---: |
| Header | `20` | `16` | `1880` | `158` |
| KPI strip | `20` | `186` | `1880` | `136` |
| Operational exposure | `20` | `334` | `1000` | `330` |
| Decision policy | `1032` | `334` | `868` | `330` |
| Confusion matrix | `20` | `676` | `1000` | `384` |
| Methodology note | `1032` | `676` | `868` | `150` |
| Executive takeaway | `1032` | `838` | `868` | `222` |

The HTML Content (lite) components use compact internal spacing and an
overflow-safe root container so that the page remains readable without
scrollbars.

## Design Assets

| Path | Purpose |
| --- | --- |
| `dashboard/themes/dataco_executive_operations_dark.json` | Shared Power BI theme. |
| `dashboard/wireframes/p01_ao1_delivery_risk_background.svg` | Minimal versioned page background. |
| `dashboard/wireframes/README.md` | Shared dashboard layout and readability standards. |

## Governance Rules

- AO1 probabilities and the high-risk flag are frozen upstream.
- The approved `35.0%` threshold is reused from the governed AO1 policy.
- Power BI does not retrain models or calculate new risk policies.
- Validation metrics are not presented as realized intervention outcomes.
- The page supports prioritization; it does not claim causal impact.

## Review Evidence

Before closing Issue `#48`, attach a final screenshot of the Power BI page to
the pull request and confirm:

- all seven visual components render without scrollbars;
- the page is legible on a `1920 x 1080` canvas;
- the displayed values match the validated metrics above; and
- the Power BI project has been saved before committing the PBIP artifacts.
