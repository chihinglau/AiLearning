"""R-06 应用信息与备案号公开接口测试。"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_app_info_public_without_auth(client: TestClient) -> None:
    response = client.get("/app/info")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == settings.app_display_name
    assert body["version"] == settings.app_version_label
    assert body["privacy_url"].endswith("/legal/privacy")
    assert body["terms_url"].endswith("/legal/terms")
    assert body["support_email"] == settings.support_email


def test_app_info_exposes_record_numbers_under_api_prefix(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "icp_record_no", "粤ICP备2026000000号-1")
    monkeypatch.setattr(settings, "app_record_no", "粤ICP备2026000000号-2A")
    monkeypatch.setattr(settings, "software_copyright_no", "2026SR0000000")
    response = client.get("/api/app/info")
    assert response.status_code == 200
    body = response.json()
    assert body["icp_record_no"] == "粤ICP备2026000000号-1"
    assert body["app_record_no"] == "粤ICP备2026000000号-2A"
    assert body["software_copyright_no"] == "2026SR0000000"
