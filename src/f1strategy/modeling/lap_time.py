"""Baseline upcoming-lap-time prediction and weekend-held-out evaluation.

WHY THIS FILE EXISTS
    ``build_lap_features`` produces leakage-safe, prior-only datasets but stops
    short of any model. This module adds the smallest honest modelling step:
    two naive reference predictors, one learned linear model, and an evaluation
    that never trains and tests on the same race weekend.

MODEL
    The learned model predicts the target lap's deviation from the driver's
    prior 3-lap mean, from three prior-only inputs: the previous lap's deviation
    from that mean, whether the previous lap is missing, and how many prior laps
    were eligible. Predicting a deviation keeps the model independent of each
    circuit's absolute lap time, so one model can be trained across circuits.
    It is a closed-form ridge regression in NumPy; no extra dependency.

SCOPE
    Rows are predictable only when at least one eligible prior lap exists in the
    window. Every model is scored on exactly the same rows. Targets include pit,
    safety-car and red-flag laps, as defined by the feature contract, so large
    errors on those laps are expected and are reported rather than filtered.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite, sqrt

import numpy as np
import pandas as pd

from f1strategy.domain.errors import InsufficientDataError
from f1strategy.features.lap_features import TARGET_COLUMN, LapFeatureDataset

PREVIOUS = "previous_lap_time_s"
PRIOR_MEAN = "prior_3lap_mean_time_s"
PRIOR_COUNT = "prior_3lap_valid_count"

MODEL_NAMES = ("ridge_deviation", "naive_previous_lap", "naive_prior_mean")

WeekendKey = tuple[int, str]


def _predictable_mask(features: pd.DataFrame) -> pd.Series:
    return features[PRIOR_MEAN].notna()


def _design_matrix(features: pd.DataFrame) -> np.ndarray:
    """Prior-only model inputs for rows that have a prior 3-lap mean."""
    prior_mean = features[PRIOR_MEAN].astype("float64").to_numpy()
    previous = features[PREVIOUS].astype("float64").to_numpy(na_value=np.nan)
    previous_missing = np.isnan(previous)
    previous_deviation = np.where(previous_missing, 0.0, previous - prior_mean)
    count = features[PRIOR_COUNT].astype("float64").to_numpy()
    return np.column_stack([previous_deviation, previous_missing.astype("float64"), count])


@dataclass(frozen=True, slots=True)
class RidgeLapTimeModel:
    """Fitted ridge model for the target lap's deviation from the prior mean."""

    intercept: float
    coefficients: tuple[float, float, float]
    feature_means: tuple[float, float, float]
    feature_scales: tuple[float, float, float]
    alpha: float
    training_rows: int

    @classmethod
    def fit(
        cls,
        datasets: Sequence[LapFeatureDataset],
        *,
        alpha: float = 1.0,
    ) -> RidgeLapTimeModel:
        """Fit on every predictable row of the supplied training datasets."""
        if isinstance(alpha, bool) or not isfinite(alpha) or alpha < 0:
            raise ValueError("alpha must be a finite number greater than or equal to 0")
        matrices: list[np.ndarray] = []
        targets: list[np.ndarray] = []
        for dataset in datasets:
            mask = _predictable_mask(dataset.features)
            subset = dataset.features.loc[mask]
            matrices.append(_design_matrix(subset))
            prior_mean = subset[PRIOR_MEAN].astype("float64").to_numpy()
            targets.append(dataset.labels.loc[mask].to_numpy(dtype="float64") - prior_mean)
        x = np.vstack(matrices) if matrices else np.empty((0, 3))
        y = np.concatenate(targets) if targets else np.empty(0)
        if len(y) < 4:
            raise InsufficientDataError(
                f"Need at least 4 predictable training rows to fit; got {len(y)}"
            )

        means = x.mean(axis=0)
        scales = x.std(axis=0)
        scales[scales == 0] = 1.0
        z = (x - means) / scales
        y_mean = float(y.mean())
        # Ridge as an augmented least-squares problem: stable for alpha == 0 and
        # for constant (zero-variance) inputs, where it returns the minimum-norm fit.
        augmented_x = np.vstack([z, sqrt(alpha) * np.eye(z.shape[1])])
        augmented_y = np.concatenate([y - y_mean, np.zeros(z.shape[1])])
        coefficients = np.linalg.lstsq(augmented_x, augmented_y, rcond=None)[0]
        return cls(
            intercept=y_mean,
            coefficients=_triple(coefficients),
            feature_means=_triple(means),
            feature_scales=_triple(scales),
            alpha=float(alpha),
            training_rows=int(len(y)),
        )

    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict lap time in seconds; rows without a prior mean are ``<NA>``."""
        result = pd.Series(pd.NA, index=features.index, dtype="Float64")
        mask = _predictable_mask(features)
        if mask.any():
            subset = features.loc[mask]
            z = (_design_matrix(subset) - np.array(self.feature_means)) / np.array(
                self.feature_scales
            )
            deviation = self.intercept + z @ np.array(self.coefficients)
            prior_mean = subset[PRIOR_MEAN].astype("float64").to_numpy()
            result.loc[mask] = prior_mean + deviation
        return result


def predict_naive_previous_lap(features: pd.DataFrame) -> pd.Series:
    """Previous lap time, falling back to the prior mean when it is missing."""
    previous = features[PREVIOUS].astype("Float64")
    fallback = features[PRIOR_MEAN].astype("Float64")
    return previous.where(previous.notna(), fallback).where(_predictable_mask(features))


def predict_naive_prior_mean(features: pd.DataFrame) -> pd.Series:
    """The driver's prior 3-lap mean."""
    return features[PRIOR_MEAN].astype("Float64").where(_predictable_mask(features))


@dataclass(frozen=True, slots=True)
class ErrorMetrics:
    """Absolute-error summary in seconds over one set of rows."""

    rows: int
    mae_s: float
    rmse_s: float
    median_ae_s: float


@dataclass(frozen=True, slots=True)
class WeekendResult:
    """Held-out scores for one race weekend, with the model trained on the others."""

    weekend: WeekendKey
    target_rows: int
    predictable_rows: int
    metrics: dict[str, ErrorMetrics]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Leave-one-weekend-out results plus scores pooled over all held-out rows."""

    weekends: tuple[WeekendResult, ...]
    pooled: dict[str, ErrorMetrics]
    alpha: float


def _metrics(errors: np.ndarray) -> ErrorMetrics:
    absolute = np.abs(errors)
    return ErrorMetrics(
        rows=int(len(errors)),
        mae_s=float(absolute.mean()),
        rmse_s=float(sqrt(float((errors**2).mean()))),
        median_ae_s=float(np.median(absolute)),
    )


def weekend_key(dataset: LapFeatureDataset) -> WeekendKey:
    """Race-weekend identity used to keep training and test data independent."""
    ref = dataset.metadata.source.ref
    return (ref.year, ref.grand_prix)


def evaluate_leave_one_weekend_out(
    datasets: Sequence[LapFeatureDataset],
    *,
    alpha: float = 1.0,
) -> EvaluationReport:
    """Hold out each race weekend in turn; train on all other weekends.

    All sessions from the same weekend are held out together, so no lap from the
    test weekend (including other sessions of that weekend) reaches training.
    Every model is scored on the same held-out predictable rows.
    """
    by_weekend: dict[WeekendKey, list[LapFeatureDataset]] = {}
    for dataset in datasets:
        if dataset.labels.name != TARGET_COLUMN:
            raise ValueError(f"dataset labels must be {TARGET_COLUMN!r}")
        by_weekend.setdefault(weekend_key(dataset), []).append(dataset)
    if len(by_weekend) < 2:
        raise InsufficientDataError(
            "Leave-one-weekend-out evaluation needs sessions from at least 2 race weekends"
        )

    results: list[WeekendResult] = []
    pooled_errors: dict[str, list[np.ndarray]] = {name: [] for name in MODEL_NAMES}
    for held_out in sorted(by_weekend):
        training = [d for key, group in by_weekend.items() if key != held_out for d in group]
        model = RidgeLapTimeModel.fit(training, alpha=alpha)
        test_rows = 0
        errors: dict[str, list[np.ndarray]] = {name: [] for name in MODEL_NAMES}
        for dataset in by_weekend[held_out]:
            features = dataset.features
            test_rows += len(features)
            mask = _predictable_mask(features).to_numpy()
            labels = dataset.labels.to_numpy(dtype="float64")[mask]
            predictions = {
                "ridge_deviation": model.predict(features),
                "naive_previous_lap": predict_naive_previous_lap(features),
                "naive_prior_mean": predict_naive_prior_mean(features),
            }
            for name, prediction in predictions.items():
                values = prediction.to_numpy(dtype="float64", na_value=np.nan)[mask]
                errors[name].append(values - labels)
        joined = {name: np.concatenate(parts) for name, parts in errors.items()}
        predictable = len(joined["ridge_deviation"])
        if predictable == 0:
            raise InsufficientDataError(f"Weekend {held_out} has no predictable rows")
        for name, values in joined.items():
            pooled_errors[name].append(values)
        results.append(
            WeekendResult(
                weekend=held_out,
                target_rows=test_rows,
                predictable_rows=predictable,
                metrics={name: _metrics(values) for name, values in joined.items()},
            )
        )

    return EvaluationReport(
        weekends=tuple(results),
        pooled={
            name: _metrics(np.concatenate(parts)) for name, parts in pooled_errors.items()
        },
        alpha=float(alpha),
    )


def _triple(values: np.ndarray) -> tuple[float, float, float]:
    first, second, third = (float(v) for v in values)
    return (first, second, third)
