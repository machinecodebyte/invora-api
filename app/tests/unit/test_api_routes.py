from fastapi.routing import APIRoute

EXPECTED_OPENAPI_TAGS = {
    "Auth",
    "Background Jobs",
    "Dashboard Analytics",
    "Forecast Results",
    "Forecast Runs",
    "Health",
    "Inventory",
    "ML Forecasting",
    "Products",
    "Reorder Recommendations",
    "Reports",
    "Sales Transactions",
    "Sales Upload",
    "System Settings",
    "Users",
}


def test_api_routes_do_not_duplicate_method_and_path(app) -> None:
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            key = (method, route.path)
            if key in seen:
                duplicates.add(key)
            seen.add(key)

    assert not duplicates, f"Duplicate API routes: {sorted(duplicates)}"


def test_openapi_includes_all_backend_route_groups(app) -> None:
    schema = app.openapi()
    tags = {
        tag
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict)
        for tag in operation.get("tags", [])
    }

    assert EXPECTED_OPENAPI_TAGS <= tags
