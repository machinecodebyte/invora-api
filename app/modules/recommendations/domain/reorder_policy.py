from __future__ import annotations

from decimal import Decimal

STOCK_QUANTUM = Decimal("0.001")


def quantize_stock(value: Decimal) -> Decimal:
    return Decimal(value).quantize(STOCK_QUANTUM)


def calculate_required_stock(
    *,
    predicted_demand: Decimal,
    safety_stock: Decimal,
) -> Decimal:
    return quantize_stock(predicted_demand + safety_stock)


def calculate_stock_gap(
    *,
    required_stock: Decimal,
    current_stock: Decimal,
) -> Decimal:
    return quantize_stock(required_stock - current_stock)


def calculate_reorder_quantity(*, stock_gap: Decimal) -> Decimal:
    if stock_gap <= 0:
        return Decimal("0.000")
    return quantize_stock(stock_gap)
