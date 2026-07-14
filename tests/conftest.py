import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
