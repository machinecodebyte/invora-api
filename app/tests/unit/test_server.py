from app.server import resolve_api_port


def _only_port_is_available(expected_port: int):
    return lambda host, port: port == expected_port


def test_resolve_api_port_uses_configured_port_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.server._is_port_available",
        _only_port_is_available(8010),
    )

    assert resolve_api_port("127.0.0.1", 8010) == 8010


def test_resolve_api_port_uses_safe_fallback_when_configured_port_is_busy(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.server._is_port_available",
        _only_port_is_available(8001),
    )

    assert resolve_api_port("127.0.0.1", 8000) == 8001
