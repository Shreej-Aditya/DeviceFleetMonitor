"""Mini device fleet monitor API. Run with: python app.py"""

# 1. Imports and app setup
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from flask import Flask, jsonify, request

app = Flask(__name__)

# 2. In-memory data: each device stores its name and latest heartbeat details.
devices = {}
TIMEOUT_SECONDS = 30
IST = timezone(timedelta(hours=5, minutes=30))


# 3. Small helpers used by the API routes.
def current_time():
    return datetime.now(timezone.utc)


def device_response(device_id, device):
    """Build the public device object and calculate ONLINE/OFFLINE."""
    heartbeat_time = device["received_at"]
    is_online = heartbeat_time is not None and (
        (current_time() - heartbeat_time).total_seconds() <= TIMEOUT_SECONDS
    )
    return {
        "id": device_id,
        "name": device["name"],
        "status": "ONLINE" if is_online else "OFFLINE",
        "last_heartbeat": device["last_heartbeat"],
        "heartbeat_status": device["heartbeat_status"],
    }


# 4. Register a device: POST /devices
@app.post("/devices")
def register_device():
    data = request.get_json(silent=True) or {}
    device_id = data.get("id")
    name = data.get("name")

    if not isinstance(device_id, str) or not device_id.strip():
        return jsonify(error="id must be a non-empty string"), 400
    if not isinstance(name, str) or not name.strip():
        return jsonify(error="name must be a non-empty string"), 400
    if device_id in devices:
        return jsonify(error="device already exists"), 409

    devices[device_id] = {
        "name": name,
        "last_heartbeat": None,
        "received_at": None,
        "heartbeat_status": None,
    }
    return jsonify(device_response(device_id, devices[device_id])), 201


# 5. Receive a heartbeat: POST /devices/<id>/heartbeat
@app.post("/devices/<device_id>/heartbeat")
def receive_heartbeat(device_id):
    if device_id not in devices:
        return jsonify(error="device not found"), 404

    data = request.get_json(silent=True) or {}
    timestamp = data.get("timestamp")
    status = data.get("status")
    if not isinstance(timestamp, str) or not isinstance(status, str) or not status.strip():
        return jsonify(error="timestamp and non-empty status are required"), 400

    try:
        parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed_time.tzinfo is None:
            raise ValueError("timezone is required")
    except ValueError:
        return jsonify(error="timestamp must be ISO 8601 and include a timezone"), 400

    device = devices[device_id]
    device["last_heartbeat"] = parsed_time.astimezone(IST).isoformat()
    device["received_at"] = current_time()  # Use server time to measure the 30-second timeout.
    device["heartbeat_status"] = status
    return jsonify(device_response(device_id, device))


# 6. Read endpoints: list, details, and fleet summary
@app.get("/devices")
def list_devices():
    return jsonify([device_response(device_id, device) for device_id, device in devices.items()])


@app.get("/devices/<device_id>")
def get_device(device_id):
    if device_id not in devices:
        return jsonify(error="device not found"), 404
    return jsonify(device_response(device_id, devices[device_id]))


@app.get("/summary")
def fleet_summary():
    statuses = [device_response(device_id, device)["status"] for device_id, device in devices.items()]
    online = statuses.count("ONLINE")
    return jsonify(total=len(statuses), online=online, offline=len(statuses) - online)


# 7. Basic automated API tests: run with `python -m unittest app -v`.
class TestFleetAPI(unittest.TestCase):
    def setUp(self):
        devices.clear()
        self.client = app.test_client()

    def register_one(self):
        return self.client.post("/devices", json={"id": "d1", "name": "Lab 1"})

    def test_register_device(self):
        response = self.register_one()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["status"], "OFFLINE")

    def test_heartbeat_and_details(self):
        self.register_one()
        response = self.client.post("/devices/d1/heartbeat", json={
            "timestamp": current_time().isoformat(), "status": "OK"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ONLINE")
        self.assertTrue(response.get_json()["last_heartbeat"].endswith("+05:30"))
        self.assertEqual(self.client.get("/devices/d1").get_json()["heartbeat_status"], "OK")

    def test_30_second_timeout(self):
        self.register_one()
        self.client.post("/devices/d1/heartbeat", json={
            "timestamp": current_time().isoformat(), "status": "OK"
        })
        now = current_time()
        devices["d1"]["received_at"] = now - timedelta(seconds=30)
        with patch(__name__ + ".current_time", return_value=now):
            self.assertEqual(self.client.get("/devices/d1").get_json()["status"], "ONLINE")
        devices["d1"]["received_at"] = now - timedelta(seconds=31)
        with patch(__name__ + ".current_time", return_value=now):
            self.assertEqual(self.client.get("/devices/d1").get_json()["status"], "OFFLINE")

    def test_summary_counts_devices(self):
        self.register_one()
        self.client.post("/devices", json={"id": "d2", "name": "Lab 2"})
        self.assertEqual(self.client.get("/summary").get_json(), {
            "total": 2, "online": 0, "offline": 2
        })


# 8. Start the local development server
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
