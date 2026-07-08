from __future__ import annotations

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from app.modules.forecasting.ml.features import FEATURE_COLUMNS

MODEL_NAME = "random_forest_regressor_v1"
FALLBACK_MODEL_NAME = "recent_average_baseline_v1"
COMBINED_MODEL_NAME = "random_forest_with_recent_average_fallback_v1"
RANDOM_STATE = 42
MIN_MODEL_ROWS = 10
MIN_VALIDATION_DAYS = 2


def train_model(frame: pd.DataFrame) -> RandomForestRegressor | None:
    if len(frame) < MIN_MODEL_ROWS:
        return None
    model = _new_model()
    model.fit(frame[list(FEATURE_COLUMNS)], frame["quantity"])
    return model


def train_with_validation(
    frame: pd.DataFrame,
) -> tuple[RandomForestRegressor | None, pd.DataFrame, pd.DataFrame]:
    unique_dates = sorted(frame["sale_date"].dt.date.unique().tolist())
    if len(frame) < MIN_MODEL_ROWS or len(unique_dates) < MIN_VALIDATION_DAYS + 2:
        return train_model(frame), frame, pd.DataFrame(columns=frame.columns)

    validation_day_count = min(7, max(1, len(unique_dates) // 5))
    validation_dates = set(unique_dates[-validation_day_count:])
    train_frame = frame[~frame["sale_date"].dt.date.isin(validation_dates)]
    validation_frame = frame[frame["sale_date"].dt.date.isin(validation_dates)]
    if len(train_frame) < MIN_MODEL_ROWS or validation_frame.empty:
        return train_model(frame), frame, pd.DataFrame(columns=frame.columns)

    validation_model = _new_model()
    validation_model.fit(train_frame[list(FEATURE_COLUMNS)], train_frame["quantity"])
    final_model = train_model(frame)
    return final_model, train_frame, validation_frame.assign(
        predicted=validation_model.predict(validation_frame[list(FEATURE_COLUMNS)])
    )


def _new_model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=80,
        random_state=RANDOM_STATE,
        min_samples_leaf=1,
        n_jobs=1,
    )
