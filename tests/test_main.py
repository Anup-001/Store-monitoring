import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_report_valid_id():
    report_id = "60084ab4-df10-42aa-b0eb-c27055233be4"  # Replace with any valid ID from reports/
    response = client.get(f"/get_report?report_id={report_id}")
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "status" in data or "csv" in data or "error" not in data

def test_trigger_report():
    response = client.post("/trigger_report")
    assert response.status_code == 200
    assert "report_id" in response.json()

def test_trigger_and_get_report():
    # Step 1: Trigger report generation
    trigger_response = client.post("/trigger_report")
    assert trigger_response.status_code == 200
    report_id = trigger_response.json().get("report_id")
    assert report_id is not None

    # Step 2: Poll /get_report until report is ready
    for _ in range(10):  # Try up to 10 times
        get_response = client.get(f"/get_report?report_id={report_id}")
        if get_response.status_code == 200:
            # If FileResponse, content-type will be 'text/csv'
            if get_response.headers.get("content-type", "").startswith("text/csv"):
                print("Report file is ready and returned as CSV.")
                assert get_response.content  # File should not be empty
                break
            data = get_response.json()
            if data.get("status") == "Running":
                time.sleep(1)  # Wait and retry
            elif "error" in data:
                assert False, f"API error: {data['error']}"
        else:
            assert False, f"Unexpected status code: {get_response.status_code}"
    else:
        assert False, "Report file was not ready after polling."