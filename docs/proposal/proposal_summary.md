# DataCo Capstone Proposal Summary

This summary captures the non-sensitive project guidance from the approved capstone proposal.

## Project Focus

The project builds a pre-shipment decision-support analytics framework for global e-commerce supply chain operations using the DataCo Smart Supply Chain dataset.

The framework combines:

- AO1: late-delivery risk prediction
- AO2: order-level profitability estimation
- AO3: risk-margin prioritization for operational decision support
- Executive dashboard outputs for tactical and strategic decisions

## Research Question	 

How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain? 

## Hypotheses 

**H1.** For late-delivery prediction, an XGBoost classifier will outperform logistic regression on held-out data, particularly in AUC-ROC and recall. 

**H2.** For order-profitability estimation, a gradient boosting regressor will outperform linear or ridge regression on held-out data, particularly in RMSE and MAE. 

**H3.** Combining predicted late-delivery risk and expected order profitability in a risk–margin framework will identify pre-dispatch priority groups that are not evident from either signal alone and therefore support differentiated operational actions.  

## Dataset

Primary dataset:

- DataCo Smart Supply Chain for Big Data Analysis
- Source: Mendeley Data, V5
- DOI: `10.17632/8gx2fvg2k6.5`
- Expected scale: approximately 180,519 transactions and 53 variables
- Period covered: 2015 to 2018

A companion metadata file should be used to verify variable meanings and support consistent preprocessing.

## Data Architecture

The project follows a simplified Medallion architecture:

- Bronze: raw data ingestion with no manual modification
- Silver: cleaning, standardization, and feature engineering
- Gold: leakage-safe analytical tables for modeling and dashboarding

## Leakage-Control Rules

The analytical design must reflect pre-shipment decision conditions.

For AO1, predictors must be limited to information available at order creation. Post-shipment variables such as `Days for Shipping (Real)`, `Shipping Date`, and `Delivery Status` must be excluded from predictive inputs.

Preprocessing steps, including imputation, encoding, scaling, resampling, and aggregate feature generation, must be fit on training data only and then applied to validation and test data.

## Modeling Plan

AO1 will compare Logistic Regression as an interpretable baseline against XGBoost as the primary classifier.

AO2 will compare Linear or Ridge Regression as baseline models against Gradient Boosting as the primary nonlinear regressor.

AO3 will combine AO1 and AO2 outputs into a 2x2 operational risk-margin matrix. A clustering extension may be added only if time permits and it improves interpretation.

## Target Definitions and Predictor Policy

AO1 uses `Late_delivery_risk` as the binary classification target. Before modeling, the team must validate the meaning of this label, its class distribution, and whether any edge cases could affect interpretation.

AO2 should use a raw order-level profit field as the primary regression target, preferably `Order Profit Per Order` or the equivalent available field such as `Benefit per order`, depending on the verified dataset schema.

`Order Item Profit Ratio` should not be used as the primary AO2 target unless explicitly justified. Profit-ratio fields, duplicate profit fields, or variables that mechanically reconstruct the profit target should be excluded from AO2 predictors or documented as descriptive-only fields.

Before AO2 modeling is finalized, the team must complete an AO2 target-reconstruction audit.

## Feature Availability and Leakage Audit

Before modeling, each candidate variable must be classified according to decision-time availability:

- available at order creation
- available before dispatch
- post-shipment
- post-delivery
- unknown / needs review

Only variables available at order creation or before dispatch may be used as predictors. Unknown variables require review before inclusion.

The feature availability matrix and leakage audit must be documented in `/docs`.

## Evaluation Strategy

The train/test split should be chronological by order date, with the most recent 20% reserved as the final held-out test set.

AO1 evaluation should focus on AUC-ROC, recall, precision, F1-score, and confusion-matrix review.

AO2 evaluation should focus on RMSE, MAE, R-squared, residual review, and basic multicollinearity screening.

AO3 must evaluate whether the combined risk-margin framework adds decision value beyond single-signal prioritization.

The team should compare:

- late-delivery-risk-only prioritization
- expected-profitability-only prioritization
- combined risk-margin prioritization

This comparison is required to support H3.

## Implementation Scope

The implementation environment uses Python, PySpark, Spark, Delta Lake, SQL, Databricks, GitHub, and Power BI.

The project should remain focused on reproducible analytics and decision support rather than unnecessary infrastructure complexity.
