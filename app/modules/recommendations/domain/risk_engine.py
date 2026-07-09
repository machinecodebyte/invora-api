from __future__ import annotations

from decimal import Decimal


def calculate_risk_level(
    *,
    predicted_demand: Decimal,
    current_stock: Decimal,
    required_stock: Decimal,
    reorder_quantity: Decimal,
) -> str:
    if current_stock <= 0 and predicted_demand > 0:
        return "critical"
    if predicted_demand > 0 and current_stock >= required_stock * Decimal("2"):
        return "overstocked"
    if reorder_quantity > 0 and current_stock < predicted_demand:
        return "high"
    if (
        reorder_quantity > 0
        and current_stock >= predicted_demand
        and current_stock < required_stock
    ):
        return "medium"
    return "low"


def recommended_action_for_risk(risk_level: str) -> str:
    if risk_level in {"critical", "high"}:
        return "reorder_now"
    if risk_level == "medium":
        return "monitor"
    if risk_level == "overstocked":
        return "overstock_review"
    return "no_reorder_needed"


def recommendation_reason(
    *,
    risk_level: str,
    predicted_demand: Decimal,
    current_stock: Decimal,
    required_stock: Decimal,
    reorder_quantity: Decimal,
) -> str:
    if risk_level == "critical":
        return "Current stock is depleted while forecasted demand is positive."
    if risk_level == "high":
        return "Current stock is below forecasted demand."
    if risk_level == "medium":
        return "Current stock covers demand but is below demand plus safety stock."
    if risk_level == "overstocked":
        return "Current stock is at least twice the required stock for the horizon."
    if reorder_quantity <= 0:
        return "Current stock covers forecasted demand and safety stock."
    return (
        "Recommended quantity is based on forecasted demand, safety stock, "
        "and current stock."
    )
