# Table 4. AO2 Model Validation Comparison

Source artifacts: `report/tables/ao2_model_validation_comparison.csv`, `report/tables/ao2_results_h2_summary.csv`, `docs/ao2_results_h2.md`.

| Model | Model type | RMSE | MAE | R-squared | Median absolute error | Mean error | Conclusion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Gradient Boosting / XGBoost Regressor | `xgboost.XGBRegressor` | 95.62030998471721 | 52.646255065500654 | 0.011785892044576474 | 31.395399094682617 | 0.9627362709037213 | Primary nonlinear model improved RMSE and MAE over Ridge. |
| Ridge Regression baseline | `sklearn.linear_model.Ridge` | 96.8276235490268 | 54.21910781630418 | -0.0133262689653563 | 32.55914083289695 | 0.6453064001768685 | Baseline comparator. |

H2 interpretation: H2 is supported on chronological validation evidence with modest support.

Caveat: final-test performance is not claimed. Residual errors remain large, predictions are compressed toward the mean, and the AO2 target-reconstruction decision remains `accepted_with_caution`.
