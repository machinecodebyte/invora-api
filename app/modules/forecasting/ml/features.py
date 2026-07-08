from __future__ import annotations

from datetime import date

import pandas as pd

FEATURE_COLUMNS = (
    "product_code",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "lag_1",
    "lag_7",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
)


def product_code_map(product_ids: list[str]) -> dict[str, int]:
    return {product_id: index for index, product_id in enumerate(sorted(product_ids))}


def build_feature_frame(
    daily_sales: pd.DataFrame,
    *,
    product_codes: dict[str, int] | None = None,
) -> pd.DataFrame:
    frame = daily_sales.copy()
    if product_codes is None:
        product_codes = product_code_map(frame["product_id"].unique().tolist())
    frame["product_code"] = (
        frame["product_id"].map(product_codes).fillna(-1).astype(int)
    )
    frame = _add_calendar_features(frame)
    frame = _add_history_features(frame)
    return frame


def future_feature_row(
    *,
    product_id: str,
    forecast_date: date,
    product_code: int,
    history: list[float],
) -> dict[str, float | int]:
    timestamp = pd.Timestamp(forecast_date)
    previous = history[-1] if history else 0.0
    lag_7 = history[-7] if len(history) >= 7 else 0.0
    recent_7 = history[-7:] if history else []
    recent_14 = history[-14:] if history else []
    return {
        "product_id": product_id,
        "sale_date": timestamp,
        "product_code": product_code,
        "day_of_week": int(timestamp.dayofweek),
        "day_of_month": int(timestamp.day),
        "month": int(timestamp.month),
        "is_weekend": int(timestamp.dayofweek >= 5),
        "lag_1": float(previous),
        "lag_7": float(lag_7),
        "rolling_mean_7": _mean(recent_7),
        "rolling_mean_14": _mean(recent_14),
        "rolling_std_7": _std(recent_7),
    }


def _add_calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame["sale_date"] = pd.to_datetime(frame["sale_date"])
    frame["day_of_week"] = frame["sale_date"].dt.dayofweek.astype(int)
    frame["day_of_month"] = frame["sale_date"].dt.day.astype(int)
    frame["month"] = frame["sale_date"].dt.month.astype(int)
    frame["is_weekend"] = (frame["day_of_week"] >= 5).astype(int)
    return frame


def _add_history_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values(["product_id", "sale_date"]).copy()
    grouped = frame.groupby("product_id", group_keys=False)["quantity"]
    frame["lag_1"] = grouped.shift(1)
    frame["lag_7"] = grouped.shift(7)
    frame["rolling_mean_7"] = frame.groupby("product_id", group_keys=False)[
        "quantity"
    ].transform(lambda values: values.shift(1).rolling(7, min_periods=1).mean())
    frame["rolling_mean_14"] = frame.groupby("product_id", group_keys=False)[
        "quantity"
    ].transform(lambda values: values.shift(1).rolling(14, min_periods=1).mean())
    frame["rolling_std_7"] = frame.groupby("product_id", group_keys=False)[
        "quantity"
    ].transform(lambda values: values.shift(1).rolling(7, min_periods=2).std())
    for column in (
        "lag_1",
        "lag_7",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_std_7",
    ):
        frame[column] = frame[column].fillna(0.0)
    return frame


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    series = pd.Series(values, dtype=float)
    return float(series.std())
