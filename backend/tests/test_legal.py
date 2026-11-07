from app.legal import PRIVACY_VERSION, TERMS_VERSION
from app.models.legal import ConsentRecord
from app.models.user import AuditLog
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_legal_documents_public_without_auth(client: TestClient) -> None:
    response = client.get("/legal/privacy")
    assert response.status_code == 200
    body = response.json()
    assert body["doc_type"] == "privacy"
    assert body["version"] == PRIVACY_VERSION
    assert "深爱学" in body["content"]
    assert body["url"].endswith("/legal/privacy")

    terms = client.get("/api/legal/terms")
    assert terms.status_code == 200
    assert terms.json()["version"] == TERMS_VERSION

    policies = client.get("/legal/policies")
    assert policies.status_code == 200
    assert {item["doc_type"] for item in policies.json()["documents"]} == {
        "privacy",
        "terms",
    }


def test_legal_document_renders_html_for_browser(client: TestClient) -> None:
    response = client.get("/legal/privacy", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<h1>" in response.text
    assert "隐私政策" in response.text


def test_legal_consent_requires_login(client: TestClient) -> None:
    response = client.post(
        "/api/legal/consent",
        json={"privacy_version": PRIVACY_VERSION, "terms_version": TERMS_VERSION},
    )
    assert response.status_code == 401


def test_legal_consent_rejects_outdated_version(
    client: TestClient, student_headers: dict[str, str], db: Session
) -> None:
    response = client.post(
        "/api/legal/consent",
        headers=student_headers,
        json={"privacy_version": "2020.01.01", "terms_version": TERMS_VERSION},
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "POLICY_VERSION_MISMATCH"
    assert detail["current"]["privacy"] == PRIVACY_VERSION
    assert db.scalar(select(func.count(ConsentRecord.id))) == 0


def test_legal_consent_records_and_clears_reconsent(
    client: TestClient, student_headers: dict[str, str], db: Session
) -> None:
    before = client.get("/api/auth/me", headers=student_headers)
    assert before.json()["needs_reconsent"] is True

    payload = {"privacy_version": PRIVACY_VERSION, "terms_version": TERMS_VERSION}
    response = client.post("/api/legal/consent", headers=student_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["privacy_version"] == PRIVACY_VERSION

    after = client.get("/api/auth/me", headers=student_headers)
    body = after.json()
    assert body["needs_reconsent"] is False
    assert body["privacy_version"] == PRIVACY_VERSION
    assert body["terms_version"] == TERMS_VERSION

    assert db.scalar(select(func.count(ConsentRecord.id))) == 2
    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "legal.consent.accepted")
    )
    assert audit is not None

    # 重复同意幂等，不新增记录。
    client.post("/api/legal/consent", headers=student_headers, json=payload)
    assert db.scalar(select(func.count(ConsentRecord.id))) == 2


def test_child_registration_requires_guardian_consent(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "phone": "13600000021",
            "password": "pass1234",
            "grade": 3,
            "is_child": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GUARDIAN_CONSENT_REQUIRED"

    ok = client.post(
        "/api/auth/register",
        json={
            "phone": "13600000022",
            "password": "pass1234",
            "grade": 3,
            "is_child": True,
            "guardian_consent": True,
            "privacy_version": PRIVACY_VERSION,
            "terms_version": TERMS_VERSION,
        },
    )
    assert ok.status_code == 201, ok.text
    records = list(db.scalars(select(ConsentRecord)))
    assert len(records) == 2
    assert all(record.guardian_confirmed for record in records)
