from fastapi.testclient import TestClient


def test_get_index(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200


def test_get_status(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "interpreter_available" in data
    assert "python_version" in data
    assert "os" in data


def test_get_settings(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "auto_run" in data
    assert "system_message" in data


def test_create_chat(client: TestClient) -> None:
    response = client.post("/api/chats")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "Percakapan Baru"
    assert data["messages"] == []


def test_get_chats(client: TestClient) -> None:
    response = client.get("/api/chats")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_chat_not_found(client: TestClient) -> None:
    response = client.get("/api/chats/nonexistent")
    assert response.status_code == 404


def test_delete_nonexistent_chat(client: TestClient) -> None:
    response = client.delete("/api/chats/nonexistent")
    assert response.status_code == 404


def test_create_and_delete_chat(client: TestClient) -> None:
    create_resp = client.post("/api/chats")
    chat_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/chats/{chat_id}")
    assert get_resp.status_code == 200

    delete_resp = client.delete(f"/api/chats/{chat_id}")
    assert delete_resp.status_code == 200

    get_resp2 = client.get(f"/api/chats/{chat_id}")
    assert get_resp2.status_code == 404


def test_whatsapp_status(client: TestClient) -> None:
    response = client.get("/api/whatsapp/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "phone" in data
    assert "qr" in data
    assert data["status"] in ("disconnected", "connecting")


def test_shutdown_endpoint_returns_message(client: TestClient) -> None:
    from unittest.mock import patch

    with patch("app.routes.system.os.kill"):
        response = client.post("/api/shutdown")
        assert response.status_code == 200
        assert "message" in response.json()
