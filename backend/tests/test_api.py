from __future__ import annotations

import os
from datetime import date, timedelta

os.environ["LEDGERFLOW_DATABASE_URL"] = "sqlite:///./test-ledgerflow.db"
os.environ["LEDGERFLOW_UPLOAD_DIR"] = "./test-uploads"
os.environ["LEDGERFLOW_SEED_DEMO"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def create_demo_client(client: TestClient) -> dict:
    response = client.post(
        "/api/clients",
        json={
            "name": "Example Studio",
            "email": "finance@example.com",
            "industry": "Creative services",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_and_empty_dashboard(client: TestClient) -> None:
    assert client.get("/api/health").json()["status"] == "ok"
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["requirements"] == 0


def test_document_review_completes_requirement(client: TestClient) -> None:
    customer = create_demo_client(client)
    period = date.today().strftime("%Y-%m")
    requirement_response = client.post(
        "/api/requirements",
        json={
            "client_id": customer["id"],
            "period": period,
            "document_type": "invoice",
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
        },
    )
    assert requirement_response.status_code == 201
    requirement = requirement_response.json()

    content = (
        f"Invoice Number INV-2048\nInvoice Date: {period}-02\n"
        "Total Amount: $1,245.00 USD\nAmount Due: $1,245.00"
    ).encode()
    upload_response = client.post(
        "/api/documents/upload",
        data={"client_id": customer["id"], "requirement_id": requirement["id"]},
        files={"file": (f"invoice_{period}.txt", content, "text/plain")},
    )
    assert upload_response.status_code == 201, upload_response.text
    uploaded = upload_response.json()
    assert uploaded["document_type"] == "invoice"
    assert uploaded["requirement_id"] == requirement["id"]
    assert uploaded["extracted_data"]["fields"]["total_amount"] == "$1,245.00"

    review_response = client.post(
        f"/api/documents/{uploaded['id']}/review",
        json={"decision": "approve", "notes": "Verified against the original."},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "approved"

    requirements = client.get("/api/requirements").json()
    assert requirements[0]["status"] == "received"
    assert client.get("/api/dashboard").json()["completion_rate"] == 100


def test_duplicate_upload_is_rejected(client: TestClient) -> None:
    customer = create_demo_client(client)
    content = b"Invoice Number INV-77\nTotal Amount $15.00 USD"
    first = client.post(
        "/api/documents/upload",
        data={"client_id": customer["id"]},
        files={"file": ("invoice.txt", content, "text/plain")},
    )
    second = client.post(
        "/api/documents/upload",
        data={"client_id": customer["id"]},
        files={"file": ("invoice-copy.txt", content, "text/plain")},
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert "Duplicate" in second.json()["detail"]


def test_reminder_and_csv_export(client: TestClient) -> None:
    customer = create_demo_client(client)
    requirement = client.post(
        "/api/requirements",
        json={
            "client_id": customer["id"],
            "period": date.today().strftime("%Y-%m"),
            "document_type": "bank_statement",
            "due_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    ).json()
    reminder = client.post(f"/api/requirements/{requirement['id']}/remind")
    assert reminder.status_code == 200
    assert reminder.json()["recipient"] == customer["email"]

    repeated = client.post(f"/api/requirements/{requirement['id']}/remind")
    assert repeated.status_code == 200
    assert repeated.json()["id"] == reminder.json()["id"]

    requirements = client.get("/api/requirements").json()
    current = next(item for item in requirements if item["id"] == requirement["id"])
    assert current["reminder_count"] == 1

    exported = client.get("/api/export/requirements.csv")
    assert exported.status_code == 200
    assert "Example Studio" in exported.text
    assert "bank_statement" in exported.text
