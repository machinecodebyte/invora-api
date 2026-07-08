from __future__ import annotations

from importlib.util import find_spec

from app.modules.forecasting.ml.dto import MLDependencyStatus


def check_ml_dependencies() -> MLDependencyStatus:
    return MLDependencyStatus(
        pandas_available=find_spec("pandas") is not None,
        numpy_available=find_spec("numpy") is not None,
        scikit_learn_available=find_spec("sklearn") is not None,
    )
