# Mini Device Fleet Monitor

A small Flask API that registers devices, receives heartbeats, and calculates whether each device is online. A device stays `ONLINE` for 30 seconds after the server receives its last heartbeat, then becomes `OFFLINE`.

## Files

- `app.py` — API, status logic, and automated tests.
- `simulator.py` — registers five sample devices and sends heartbeats.

## Install and run

Use Python 3.8 or later. Install Flask:

```sh
python -m pip install Flask
```

Start the API:

```sh
python app.py
```

In a second terminal, start the five default simulated devices:

```sh
python simulator.py
```

You can provide your own five or more device IDs and names. Repeat `--device ID:NAME` for each device:

```sh
python simulator.py --device lab-a:Chemistry-Lab --device lab-b:Library --device lab-c:Room-12 --device lab-d:Room-14 --device lab-e:Workshop
```

To see a device transition from online to offline, run:

```sh
python simulator.py --stop device-03
```

The simulator first sends heartbeats for all devices for 35 seconds, then stops `device-03` while the others continue. After a further 30 seconds without a heartbeat, it should show as offline. Use `--stop-after 45` to keep it online longer before stopping it. With custom device names, use that device's ID after `--stop` (for example, `--stop lab-c`). Press Ctrl+C to stop either program. The API listens at `http://127.0.0.1:8000`.

## API examples

```sh
curl -X POST http://127.0.0.1:8000/devices -H "Content-Type: application/json" -d '{"id":"device-01","name":"Lab Device 01"}'
curl -X POST http://127.0.0.1:8000/devices/device-01/heartbeat -H "Content-Type: application/json" -d '{"timestamp":"2026-09-21T10:30:00Z","status":"OK"}'
curl http://127.0.0.1:8000/devices
curl http://127.0.0.1:8000/devices/device-01
curl http://127.0.0.1:8000/summary
```

## How to explain it

1. **The `devices` dictionary** holds device names and their latest heartbeat data. It resets when the app stops.
2. **`device_response`** calculates online/offline status each time an API response is made. It uses the server's receive time, so device clock differences do not affect the 30-second timeout. Exactly 30 seconds is still online.
3. **POST routes** register a device or save a heartbeat. They return a clear error for invalid input, unknown devices, or duplicate IDs.
4. **GET routes** list devices, show one device, or count the fleet.
5. **`simulator.py`** acts like five or more devices by calling the same HTTP endpoints repeatedly. Its default IDs are examples; pass `--device ID:NAME` to customize them.
6. **Tests in `app.py`** use Flask's test client, so they do not need the server running.

## Tests

```sh
python -m unittest app -v
```

## Assumptions and limitations

- Device IDs are unique and case-sensitive.
- The server's receive time controls online/offline status. The API returns `last_heartbeat` in India Standard Time (`+05:30`), regardless of the timezone sent by the device.
- Data stays in memory and is lost when the server stops. This small demo has no authentication or database.

## If I had one more day

I would add a small database and more tests for invalid requests, then configure the server address and port outside the code.

## AI Usage

I used OpenAI Codex to help draft and simplify the API, simulator, tests, and README. I kept the API and tests together in `app.py` to keep the project simple. I reviewed the timeout logic so the server's receive time controls device status. I ran the four API tests, checked that both Python files compile, and checked the simulator command-line help.
