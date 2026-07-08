from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd

from app.modules.forecasting.ml.dto import ActiveProductInput, SalesRecordInput


def active_products_from_objects(products: list[Any]) -> list[ActiveProductInput]:
    return [
        ActiveProductInput(
            id=product.id,
            sku=product.sku,
            name=product.name,
        )
        for product in products
    ]


def sales_records_from_objects(records: list[Any]) -> list[SalesRecordInput]:
    clean_records: list[SalesRecordInput] = []
    for record in records:
        if record.sale_date is None or record.quantity is None:
            continue
        quantity = Decimal(str(record.quantity))
        if quantity <= 0:
            continue
        clean_records.append(
            SalesRecordInput(
                product_id=record.product_id,
                sale_date=record.sale_date,
                quantity=quantity,
            )
        )
    return clean_records


def aggregate_daily_sales(
    *,
    products: list[ActiveProductInput],
    sales_records: list[SalesRecordInput],
) -> pd.DataFrame:
    product_ids = [str(product.id) for product in products]
    if not product_ids:
        return pd.DataFrame(columns=["product_id", "sale_date", "quantity"])

    records = [
        {
            "product_id": str(record.product_id),
            "sale_date": pd.Timestamp(record.sale_date),
            "quantity": float(record.quantity),
        }
        for record in sales_records
        if str(record.product_id) in product_ids and record.quantity > 0
    ]
    if records:
        sales_frame = pd.DataFrame(records)
        grouped = (
            sales_frame.groupby(["product_id", "sale_date"], as_index=False)[
                "quantity"
            ]
            .sum()
            .sort_values(["product_id", "sale_date"])
        )
        start_date = grouped["sale_date"].min()
        end_date = grouped["sale_date"].max()
    else:
        grouped = pd.DataFrame(columns=["product_id", "sale_date", "quantity"])
        today = pd.Timestamp.utcnow().normalize().tz_localize(None)
        start_date = today
        end_date = today

    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    grid = pd.MultiIndex.from_product(
        [product_ids, date_range],
        names=["product_id", "sale_date"],
    ).to_frame(index=False)
    daily = grid.merge(grouped, on=["product_id", "sale_date"], how="left")
    daily["quantity"] = daily["quantity"].fillna(0.0).astype(float)
    return daily.sort_values(["product_id", "sale_date"]).reset_index(drop=True)
