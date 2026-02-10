"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealthCheck:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "typedb_connected" in data


class TestQueryEndpoint:
    def test_query(self, client):
        response = client.post(
            "/api/v1/query",
            json={"query": "Why was Acme given a 20% discount?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "paths_found" in data

    def test_query_empty(self, client):
        response = client.post(
            "/api/v1/query",
            json={"query": ""},
        )
        assert response.status_code == 422  # validation error


class TestEntityEndpoints:
    def test_create_entity(self, client):
        response = client.post(
            "/api/v1/entities",
            json={
                "entity_id": "cust_001",
                "entity_name": "Acme Corp",
                "entity_type": "customer",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["entity_id"] == "cust_001"

    def test_get_entity_no_db(self, client):
        response = client.get("/api/v1/entities/cust_001")
        assert response.status_code == 503

    def test_list_entities_no_db(self, client):
        response = client.get("/api/v1/entities")
        assert response.status_code == 503

    def test_delete_entity_no_db(self, client):
        response = client.delete("/api/v1/entities/cust_001")
        assert response.status_code == 503


class TestHyperedgeEndpoints:
    def test_create_hyperedge(self, client):
        response = client.post(
            "/api/v1/hyperedges",
            json={
                "hyperedge_id": "he_001",
                "relation_type": "decision-event",
                "participants": [
                    {"entity_id": "cust_001", "role": "involved-entity"},
                    {"entity_id": "emp_001", "role": "decision-maker"},
                ],
                "decision_type": "discount-approval",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["hyperedge_id"] == "he_001"
        assert len(data["participants"]) == 2

    def test_create_hyperedge_min_participants(self, client):
        response = client.post(
            "/api/v1/hyperedges",
            json={
                "hyperedge_id": "he_bad",
                "participants": [
                    {"entity_id": "cust_001", "role": "p"},
                ],
            },
        )
        assert response.status_code == 422  # needs at least 2 participants

    def test_get_hyperedges_no_db(self, client):
        response = client.get("/api/v1/hyperedges/cust_001")
        assert response.status_code == 503

    def test_s_adjacent_no_db(self, client):
        response = client.post(
            "/api/v1/hyperedges/s-adjacent",
            json={"entity_id": "cust_001", "s": 2},
        )
        assert response.status_code == 503
