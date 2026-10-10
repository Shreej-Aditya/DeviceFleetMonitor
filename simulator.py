"""Simulate five or more devices; use --device ID:NAME to customize them."""
import argparse
from datetime import datetime, timezone
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"


def post(path: str, body: dict):
    request = Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=3) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=5, help="heartbeat interval in seconds")
    parser.add_argument("--device", action="append", metavar="ID:NAME", help="device to simulate; provide at least five (repeat this option)")
    parser.add_argument("--stop", action="append", default=[], metavar="DEVICE_ID", help="stop this device after the initial online period (repeatable)")
    parser.add_argument("--stop-after", type=float, default=35, help="seconds to send heartbeats before stopping selected devices")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.stop and args.stop_after < 30:
        parser.error("--stop-after must be at least 30 seconds to show the device online first")
    if args.stop and args.interval >= args.stop_after:
        parser.error("--interval must be shorter than --stop-after")

    if args.device:
        devices = []
        for item in args.device:
            if ":" not in item:
                parser.error("--device must use ID:NAME format")
            device_id, name = item.split(":", 1)
            if not device_id.strip() or not name.strip():
                parser.error("device ID and name cannot be empty")
            devices.append((device_id.strip(), name.strip()))
        if len(devices) < 5:
            parser.error("provide at least five --device options")
        if len({device_id for device_id, _ in devices}) != len(devices):
            parser.error("device IDs must be unique")
    else:
        devices = [(f"device-{i:02d}", f"Lab Device {i:02d}") for i in range(1, 6)]

    device_ids = [device_id for device_id, _ in devices]
    stopped = set(args.stop)
    unknown = stopped - set(device_ids)
    if unknown:
        parser.error("unknown device id(s): " + ", ".join(sorted(unknown)))

    for device_id, name in devices:
        try:
            post("/devices", {"id": device_id, "name": name})
            print(f"Registered {device_id}")
        except HTTPError as exc:
            if exc.code != 409:
                raise
            print(f"Using existing {device_id}")
    stop_time = time.monotonic() + args.stop_after if stopped else None
    if stopped:
        print(f"Sending all heartbeats for {args.stop_after:g}s, then stopping: {', '.join(sorted(stopped))}.")
    else:
        print(f"Sending heartbeats every {args.interval:g}s. Ctrl+C exits.")
    try:
        while True:
            for device_id in device_ids:
                if device_id in stopped and time.monotonic() >= stop_time:
                    continue
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                try:
                    post(f"/devices/{device_id}/heartbeat", {"timestamp": timestamp, "status": "OK"})
                    print(f"{device_id} -> heartbeat")
                except (HTTPError, URLError) as exc:
                    print(f"{device_id} -> error: {exc}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
