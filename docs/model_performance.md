# Model Performance Metrics

This document provides a detailed breakdown of the performance metrics for all model architectures evaluated in the ARISE system.

## 1. Summary Table (Comparative Performance)

The following table summarizes the performance of the various models on the sepsis prediction task (24-hour lookback, 12-hour prediction horizon).

| Model Architecture | Task Type | AUROC | AUPRC | F1 Score | Sensitivity | Specificity | Lead Time (Avg) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DST v2 (Primary)** | Survival | 0.7957* | 0.1690 | N/A | **69.7%** | 81.31% | **28.2 Hours** |
| **Full Ensemble** | Classification | **0.9013** | **0.4256** | **0.4607** | 48.06% | 97.68% | N/A |
| **Tree Ensemble** | Classification | 0.8936 | 0.3833 | 0.4236 | 43.09% | 97.69% | N/A |
| **XGBoost** | Classification | 0.8935 | 0.3786 | 0.4208 | 43.17% | 97.63% | N/A |
| **LightGBM** | Classification | 0.8909 | 0.3802 | 0.4180 | 41.32% | 97.84% | N/A |
| **Random Forest** | Classification | 0.8791 | 0.3260 | 0.3814 | 45.76% | 96.40% | N/A |
| **LSTM (Rich)** | Sequence | 0.8787 | 0.3774 | 0.4403 | 47.82% | 97.35% | N/A |
| **LSTM (Simple)** | Sequence | 0.8579 | 0.2392 | 0.3181 | 44.12% | 94.90% | N/A |
| **Logistic Regression** | Linear | 0.8433 | 0.2174 | 0.2923 | 34.81% | 96.05% | N/A |

*\* Note: The DST v2 AUROC reflects rolling-window performance on unbalanced streaming data, whereas classification baselines are evaluated on a fixed 24h prediction window.*

## 2. Model Definitions

### DST v2 (Dynamic Survival Transformer)
*   **Architecture**: Transformer-based survival model with multi-head attention.
*   **Inputs**: 25 time-varying features (vitals/labs) + 127 static features.
*   **Strengths**: Captures long-range dependencies in ICU trajectories and provides continuous risk scoring (Survival Function).

### LSTM (Rich vs Simple)
*   **Simple**: 7 core vital signs (HR, RespRate, Temp, SBP, DBP, MAP, SpO2).
*   **Rich**: 17 features including additional laboratory indicators (Lactate, WBC, etc.) and SOFA components.

### Tree Ensemble
*   **Composition**: A weighted ensemble of XGBoost (30%), LightGBM (30%), and LSTM Rich (40%).
*   **Optimization**: Maximized for AUPRC to handle the high class imbalance of sepsis onset.

## 3. Evaluation Context

*   **Dataset**: MIMIC-IV Clinical Database (2008-2019).
*   **Sepsis Definition**: Sepsis-3 (Suspected Infection + SOFA increase ≥ 2).
*   **Lead Time**: Measures the interval between model alert and clinical sepsis onset. The DST v2 achieves a significant lead time of **28.2 hours**, enabling proactive intervention.

> [!NOTE]
> All metrics reported above were obtained using stratified 5-fold cross-validation. Detailed training logs can be found in `notebooks/03_model_training.ipynb` and `notebooks/03b_survival_modeling12.ipynb`.
