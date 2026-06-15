# Table 3. AO1 Model Validation Comparison

Source artifacts: `report/tables/ao1_model_validation_comparison.csv`, `docs/ao1_results_h1_validation.md`.

| Model | ROC-AUC | PR-AUC | Accuracy | Precision | Recall | F1 | Log loss | Conclusion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| XGBoost classifier | 0.7752787090098937 | 0.8489117912727454 | 0.7212314148247296 | 0.8890176760359316 | 0.5839730981536705 | 0.7049092440836333 | 0.5132764633696615 | Primary model. |
| Logistic Regression baseline | 0.7425530885785165 | 0.8306652164503137 | 0.6855623485149948 | 0.8295571095571096 | 0.5644946386650593 | 0.671826625386997 | 0.572337054661078 | Baseline comparator. |

H1 interpretation: XGBoost outperformed Logistic Regression on the chronological validation slice, including ROC-AUC and recall. H1 is supported on validation evidence.

Caveat: this table does not claim final-test confirmation. The final test partition remains reserved unless a separate checked artifact supports final-test wording.
