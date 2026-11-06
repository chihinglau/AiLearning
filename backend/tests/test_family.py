from fastapi.testclient import TestClient


def _register(client: TestClient, payload: dict) -> None:
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _child(client: TestClient, phone: str, grade: int = 2, is_child: bool = True) -> dict[str, str]:
    _register(
        client,
        {"phone": phone, "password": "pass1234", "grade": grade, "is_child": is_child},
    )
    return _login(client, phone)


def _parent(client: TestClient, phone: str) -> dict[str, str]:
    _register(client, {"phone": phone, "password": "pass1234", "role": "parent"})
    return _login(client, phone)


def test_binding_lifecycle(client: TestClient) -> None:
    child_headers = _child(client, "13300000001")
    parent_headers = _parent(client, "13300000002")

    created = client.post(
        "/api/family/bindings",
        json={"child_phone": "13300000001"},
        headers=parent_headers,
    )
    assert created.status_code == 201, created.text
    binding = created.json()
    assert binding["status"] == "pending"
    assert binding["consent_at"] is None
    binding_id = binding["id"]

    assert client.get("/api/family/children", headers=parent_headers).json() == []
    assert client.get("/api/auth/me", headers=child_headers).json()["guardian_consent"] is False

    confirmed = client.post(
        f"/api/family/bindings/{binding_id}/confirm", headers=child_headers
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "active"
    assert confirmed.json()["consent_at"] is not None

    children = client.get("/api/family/children", headers=parent_headers)
    assert children.status_code == 200
    assert [item["id"] for item in children.json()] == [binding["child_id"]]
    assert client.get("/api/auth/me", headers=child_headers).json()["guardian_consent"] is True

    revoked = client.delete(f"/api/family/bindings/{binding_id}", headers=parent_headers)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert client.get("/api/family/children", headers=parent_headers).json() == []
    assert client.get("/api/auth/me", headers=child_headers).json()["guardian_consent"] is False


def test_only_parent_can_request(client: TestClient) -> None:
    child_headers = _child(client, "13300000003")
    response = client.post(
        "/api/family/bindings",
        json={"child_phone": "13300000003"},
        headers=child_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_unknown_child_phone(client: TestClient) -> None:
    parent_headers = _parent(client, "13300000004")
    response = client.post(
        "/api/family/bindings",
        json={"child_phone": "13399999999"},
        headers=parent_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CHILD_NOT_FOUND"


def test_duplicate_active_binding_rejected(client: TestClient) -> None:
    child_headers = _child(client, "13300000005")
    parent_headers = _parent(client, "13300000006")
    created = client.post(
        "/api/family/bindings",
        json={"child_phone": "13300000005"},
        headers=parent_headers,
    )
    binding_id = created.json()["id"]
    client.post(f"/api/family/bindings/{binding_id}/confirm", headers=child_headers)

    again = client.post(
        "/api/family/bindings",
        json={"child_phone": "13300000005"},
        headers=parent_headers,
    )
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "ALREADY_BOUND"


def test_other_parent_cannot_confirm(client: TestClient) -> None:
    _child(client, "13300000007")
    owner = _parent(client, "13300000008")
    intruder = _parent(client, "13300000009")
    binding_id = client.post(
        "/api/family/bindings",
        json={"child_phone": "13300000007"},
        headers=owner,
    ).json()["id"]

    response = client.post(
        f"/api/family/bindings/{binding_id}/confirm", headers=intruder
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SCOPE_DENIED"


def test_revoked_binding_cannot_be_confirmed(client: TestClient) -> None:
    child_headers = _child(client, "13300000010")
    parent_headers = _parent(client, "13300000011")
    binding_id = client.post(
        "/api/family/bindings",
        json={"child_phone": "13300000010"},
        headers=parent_headers,
    ).json()["id"]
    client.delete(f"/api/family/bindings/{binding_id}", headers=parent_headers)

    response = client.post(
        f"/api/family/bindings/{binding_id}/confirm", headers=child_headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "BINDING_REVOKED"
