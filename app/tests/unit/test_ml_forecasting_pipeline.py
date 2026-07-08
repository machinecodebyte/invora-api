from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.forecasting.ml.dto import ActiveProductInput, SalesRecordInput
from app.modules.forecasting.ml.evaluation import calculate_metrics
from app.modules.forecasting.ml.features import FEATURE_COLUMNS, build_feature_frame
from app.modules.forecasting.ml.pipeline import (
    _to_demand_decimal,
    run_forecasting_pipeline,
)
from app.modules.forecasting.ml.preprocessing import (
    aggregate_daily_sales,
    sales_records_from_objects,
)
from app.modules.forecasting.ml.training import (
    COMBINED_MODEL_NAME,
    FALLBACK_MODEL_NAME,
)


@dataclass(slots=True)
class ProductObject:
    id: UUID
    sku: str
    name: str


@dataclass(slots=True)
class SalesObject:
    product_id: UUID
    sale_date: date | None
    quantity: Decimal | None


def _product(*, sku: str = "SKU-1", name: str = "Product") -> ProductObject:
    return ProductObject(id=uuid4(), sku=sku, name=name)


def _sale(product_id: UUID, day: date, quantity: Decimal | int) -> SalesObject:
    return SalesObject(
        product_id=product_id,
        sale_date=day,
        quantity=Decimal(str(quantity)),
    )


def test_sales_record_preprocessing_filters_invalid_rows() -> None:
    product_id = uuid4()

    records = sales_records_from_objects(
        [
            _sale(product_id, date(2026, 7, 1), 3),
            _sale(product_id, date(2026, 7, 2), 0),
            _sale(product_id, date(2026, 7, 3), -1),
            SalesObject(product_id=product_id, sale_date=None, quantity=Decimal("2")),
            SalesObject(
                product_id=product_id,
                sale_date=date(2026, 7, 4),
                quantity=None,
            ),
        ]
    )

    assert len(records) == 1
    assert records[0].quantity == Decimal("3")


def test_daily_sales_aggregation_fills_missing_dates_for_each_product() -> None:
    first = ActiveProductInput(id=uuid4(), sku="A", name="First")
    second = ActiveProductInput(id=uuid4(), sku="B", name="Second")

    daily_sales = aggregate_daily_sales(
        products=[first, second],
        sales_records=[
            SalesRecordInput(
                product_id=first.id,
                sale_date=date(2026, 7, 1),
                quantity=Decimal("1.500"),
            ),
            SalesRecordInput(
                product_id=first.id,
                sale_date=date(2026, 7, 1),
                quantity=Decimal("2.500"),
            ),
            SalesRecordInput(
                product_id=first.id,
                sale_date=date(2026, 7, 3),
                quantity=Decimal("5.000"),
            ),
        ],
    )

    assert len(daily_sales) == 6
    first_rows = daily_sales[daily_sales["product_id"] == str(first.id)]
    second_rows = daily_sales[daily_sales["product_id"] == str(second.id)]
    assert first_rows.iloc[0]["quantity"] == 4.0
    assert first_rows.iloc[1]["quantity"] == 0.0
    assert second_rows["quantity"].tolist() == [0.0, 0.0, 0.0]


def test_feature_generation_adds_calendar_lag_and_rolling_values() -> None:
    product = ActiveProductInput(id=uuid4(), sku="A", name="First")
    start = date(2026, 7, 1)
    daily_sales = aggregate_daily_sales(
        products=[product],
        sales_records=[
            SalesRecordInput(
                product_id=product.id,
                sale_date=start + timedelta(days=offset),
                quantity=Decimal(offset + 1),
            )
            for offset in range(8)
        ],
    )

    features = build_feature_frame(daily_sales)
    eighth_day = features.iloc[7]
    weekend_day = features[features["sale_date"].dt.date == date(2026, 7, 4)].iloc[0]

    assert set(FEATURE_COLUMNS).issubset(set(features.columns))
    assert features.iloc[1]["lag_1"] == 1.0
    assert eighth_day["lag_7"] == 1.0
    assert eighth_day["rolling_mean_7"] == 4.0
    assert weekend_day["is_weekend"] == 1


def test_metrics_are_zero_safe() -> None:
    metrics = calculate_metrics([0, 10], [2, 8])

    assert metrics["mae"] == Decimal("2.0000")
    assert metrics["rmse"] == Decimal("2.0000")
    assert metrics["mape"] == Decimal("110.0000")


def test_negative_predictions_are_clipped_when_quantized() -> None:
    assert _to_demand_decimal(-4.321) == Decimal("0.000")
    assert _to_demand_decimal(2.3456) == Decimal("2.346")


def test_pipeline_produces_deterministic_predictions_for_all_products() -> None:
    first = _product(sku="A", name="First")
    second = _product(sku="B", name="Second")
    start = date(2026, 6, 1)
    sales = [
        _sale(first.id, start + timedelta(days=offset), 5 + (offset % 3))
        for offset in range(20)
    ] + [
        _sale(second.id, start + timedelta(days=offset), 2 + (offset % 2))
        for offset in range(20)
    ]

    first_result = run_forecasting_pipeline(
        products=[first, second],
        sales_transactions=sales,
        horizon_days=7,
    )
    second_result = run_forecasting_pipeline(
        products=[first, second],
        sales_transactions=sales,
        horizon_days=7,
    )

    first_predictions = [
        (row.product_id, row.forecast_date, row.predicted_demand, row.model_name)
        for row in first_result.predictions
    ]
    second_predictions = [
        (row.product_id, row.forecast_date, row.predicted_demand, row.model_name)
        for row in second_result.predictions
    ]
    assert first_predictions == second_predictions
    assert len(first_result.predictions) == 14
    assert {row.product_id for row in first_result.predictions} == {
        first.id,
        second.id,
    }
    assert min(row.predicted_demand for row in first_result.predictions) >= Decimal(
        "0.000"
    )
    assert first_result.metrics.model_name == COMBINED_MODEL_NAME
    assert first_result.metrics.training_rows > 0
    assert first_result.metrics.validation_rows > 0


def test_pipeline_uses_fallback_for_sparse_product_history() -> None:
    strong = _product(sku="A", name="Strong")
    sparse = _product(sku="B", name="Sparse")
    start = date(2026, 6, 1)
    sales = [
        _sale(strong.id, start + timedelta(days=offset), 4 + (offset % 3))
        for offset in range(14)
    ]
    sales.append(_sale(sparse.id, start, 3))

    result = run_forecasting_pipeline(
        products=[strong, sparse],
        sales_transactions=sales,
        horizon_days=7,
    )
    sparse_predictions = [
        prediction
        for prediction in result.predictions
        if prediction.product_id == sparse.id
    ]

    assert len(result.predictions) == 14
    assert result.metrics.fallback_products == 1
    assert {prediction.model_name for prediction in sparse_predictions} == {
        FALLBACK_MODEL_NAME
    }
    assert min(prediction.predicted_demand for prediction in sparse_predictions) >= (
        Decimal("0.000")
    )
