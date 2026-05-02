# DataCo Capstone Proposal Summary

This summary captures the non-sensitive project guidance from the approved capstone proposal.

## Project Focus

The project builds a pre-shipment decision-support analytics framework for global e-commerce supply chain operations using the DataCo Smart Supply Chain dataset.

The framework combines:

- AO1: late-delivery risk prediction
- AO2: order-level profitability estimation
- AO3: risk-margin prioritization for operational decision support
- Executive dashboard outputs for tactical and strategic decisions

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

## Evaluation Strategy

The train/test split should be chronological by order date, with the most recent 20% reserved as the final held-out test set.

AO1 evaluation should focus on AUC-ROC, recall, precision, F1-score, and confusion-matrix review.

AO2 evaluation should focus on RMSE, MAE, R-squared, residual review, and basic multicollinearity screening.

AO3 evaluation should focus on whether the combined risk-margin view reveals operational priority groups that are not evident from either signal alone.

## Implementation Scope

The implementation environment uses Python, PySpark, Spark, Delta Lake, SQL, Databricks, GitHub, and Power BI.

The project should remain focused on reproducible analytics and decision support rather than unnecessary infrastructure complexity.
