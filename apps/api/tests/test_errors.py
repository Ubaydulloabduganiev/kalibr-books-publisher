"""Expected and unexpected API error behavior."""

from httpx import ASGITransport, AsyncClient

from kalibr_publisher.core.config import Settings
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.main import create_app


async def test_expected_api_error_is_safe_and_actionable(settings: Settings) -> None:
    app = create_app(settings)

    async def raise_expected_error() -> None:
        raise ApiError(
            status_code=409,
            code="state_conflict",
            message="The resource is in an incompatible state.",
            recovery_suggestion="Refresh the resource and retry the operation.",
            technical_details={"state": "locked"},
        )

    app.add_api_route("/api/v1/test-expected-error", raise_expected_error)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        response = await client.get("/api/v1/test-expected-error")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "state_conflict"
    assert response.json()["error"]["technical_details"] == {"state": "locked"}


async def test_unexpected_error_hides_exception_message(settings: Settings) -> None:
    app = create_app(settings)

    async def raise_unexpected_error() -> None:
        raise RuntimeError("sensitive internal detail")

    app.add_api_route("/api/v1/test-unexpected-error", raise_unexpected_error)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        response = await client.get("/api/v1/test-unexpected-error")

    error = response.json()["error"]
    assert response.status_code == 500
    assert error["code"] == "internal_server_error"
    assert "sensitive internal detail" not in response.text
    assert error["technical_details"] == {"exception_type": "RuntimeError"}
