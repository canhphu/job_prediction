"""Consistent holdout and cross-validation metrics for salary models."""

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate


def regression_metrics(actual, predicted) -> dict:
    return {"MAE": float(mean_absolute_error(actual, predicted)), "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))), "R2": float(r2_score(actual, predicted))}


def cross_validation_metrics(model, X, y, folds: int = 5) -> dict:
    cv = KFold(n_splits=min(folds, len(X)), shuffle=True, random_state=42)
    scores = cross_validate(model, X, y, cv=cv, scoring={"mae": "neg_mean_absolute_error", "r2": "r2"})
    return {"mae_mean": float(-scores["test_mae"].mean()), "mae_std": float(scores["test_mae"].std()), "r2_mean": float(scores["test_r2"].mean()), "r2_std": float(scores["test_r2"].std())}
