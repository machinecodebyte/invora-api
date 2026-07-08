from __future__ import annotations

from decimal import Decimal

import numpy as np


def calculate_metrics(y_true: object, y_pred: object) -> dict[str, Decimal | None]:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if actual.size == 0 or predicted.size == 0:
        return {"mae": None, "rmse": None, "mape": None}

    errors = np.abs(actual - predicted)
    mae = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean(np.square(actual - predicted))))
    denominators = np.maximum(np.abs(actual), 1.0)
    mape = float(np.mean(errors / denominators) * 100)
    return {
        "mae": _decimal_or_none(mae),
        "rmse": _decimal_or_none(rmse),
        "mape": _decimal_or_none(mape),
    }


def _decimal_or_none(value: float) -> Decimal | None:
    if not np.isfinite(value):
        return None
    return Decimal(str(value)).quantize(Decimal("0.0001"))
