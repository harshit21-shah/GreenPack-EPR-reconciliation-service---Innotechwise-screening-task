from fastapi.testclient import TestClient

from app.main import app


def test_submit_summary_and_ask_flow():
    client = TestClient(app)

    submit_response = client.post(
        "/submit",
        json={
            "producer_id": "GREENPACK-001",
            "month": "2026-04",
            "declared_quantities_kg": {
                "rigid_plastic": 12000,
                "flexible_plastic": 8500,
                "multilayer_plastic": 3200,
            },
        },
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["record_id"]

    summary_response = client.get("/summary/GREENPACK-001/2026-04")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["overall_status"] == "needs_review"
    assert [row["category"] for row in summary["reconciliation"] if row["flagged"]] == [
        "flexible_plastic"
    ]

    ask_response = client.post(
        "/ask",
        json={"question": "What evidence should GreenPack keep for an audit?"},
    )
    assert ask_response.status_code == 200
    assert ask_response.json()["citations"]
