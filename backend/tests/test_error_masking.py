from fastapi.testclient import TestClient

from app.main import app


def test_unhandled_error_is_masked(client: TestClient) -> None:
    path = "/api/_test/boom"

    async def boom() -> None:
        raise RuntimeError("secret db password leaked")

    app.add_api_route(path, boom, methods=["GET"])
    try:
        response = client.get(path)
    finally:
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "path", "") != path
        ]

    assert response.status_code == 500
    assert response.json()["detail"] == "INTERNAL_ERROR"
    assert "request_id" in response.json()
    assert "secret db password" not in response.text
    assert "Traceback" not in response.text
