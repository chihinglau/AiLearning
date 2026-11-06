"""P1-13 首页/学情缓存命中与写后失效。"""

import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import cache
from app.models.content import Question


def _login(client: TestClient, phone: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"phone": phone, "password": "pass1234", "grade": 3},
    )
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_home_and_stats_cache_hit_and_invalidate_on_practice(
    client: TestClient, db: Session
) -> None:
    headers = _login(client, "13623000011")

    assert client.get("/api/learn/home", headers=headers).status_code == 200
    assert client.get("/api/learn/stats", headers=headers).status_code == 200
    assert cache.stats()["entries"] == 2

    hits_before = cache.stats()["hits"]
    assert client.get("/api/learn/home", headers=headers).status_code == 200
    assert cache.stats()["hits"] == hits_before + 1

    # 练习提交写入答题记录并失效该用户缓存
    question = Question(
        chapter_id=1,
        subject="math",
        q_type="choice",
        content={"stem": "1 + 1 = ?"},
        answer={"value": "A"},
    )
    db.add(question)
    db.commit()
    submitted = client.post(
        "/api/practice/submit",
        headers=headers,
        json={"question_id": question.id, "user_answer": {"value": "B"}},
    )
    assert submitted.status_code == 200, submitted.text
    assert cache.stats()["entries"] == 0

    stats = client.get("/api/learn/stats", headers=headers).json()
    assert stats["total_answered"] == 1
    assert stats["accuracy"] == 0.0


def test_home_aggregate_p95_under_300ms(client: TestClient) -> None:
    """L14：缓存命中路径下首页聚合 P95 < 300ms。"""
    headers = _login(client, "13623000012")
    client.get("/api/learn/home", headers=headers)  # 预热，建立缓存

    times: list[float] = []
    for _ in range(30):
        started = time.perf_counter()
        response = client.get("/api/learn/home", headers=headers)
        times.append(time.perf_counter() - started)
        assert response.status_code == 200, response.text
    times.sort()
    p95 = times[max(0, int(len(times) * 0.95) - 1)]
    print(f"\nhome p95={p95 * 1000:.2f}ms")
    assert p95 < 0.3


def test_cache_invalidate_user_prefix() -> None:
    cache.clear()
    cache.set("home:7:3:first", "a")
    cache.set("home:7:4:first", "b")
    cache.set("stats:7", "c")
    cache.invalidate_user(7)
    assert cache.get("home:7:3:first") is None
    assert cache.get("home:7:4:first") is None
    assert cache.get("stats:7") is None

    cache.set("home:8:3:first", "d")
    cache.invalidate_prefix("home:8:")
    assert cache.get("home:8:3:first") is None
    cache.clear()
