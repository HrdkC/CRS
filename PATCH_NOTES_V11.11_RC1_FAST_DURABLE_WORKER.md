# CRS V11.11-RC1 — Fast Durable PLC Worker Patch

## Confirmed cause

The Flask web application only queues PLC work. Restore, Save, Upload, and
Download do not move until `scripts/run_plc_worker.py` is running. Starting the
worker only after pressing an operation therefore leaves the screen at 0%.

## Changes

- Adds a one-click launcher that starts the web application and durable worker.
- Keeps PLC writes outside the Flask process.
- Reduces idle queue polling from 2 seconds to 0.25 seconds.
- Publishes a one-second worker heartbeat under `instance`.
- Rejects a PLC operation immediately when the worker is offline instead of
  taking locks and leaving the browser waiting indefinitely.
- Prevents two fresh durable workers from running at the same time.
- Adds a matching stop launcher.

## Normal startup

Double-click:

`Start_CRS_With_PLC_Worker.bat`

Type `START` once. The launcher starts the worker first, waits for its heartbeat,
and then starts the web application.

## Expected response time

With the worker online, a newly queued operation should normally be claimed in
0.25 to 1 second. PLC connection, array size, phase strings, readback, and
handshake duration are separate and can take longer.

## Safety

The launcher explicitly enables live PLC communication only for its child
processes. The web process still never executes PLC writes. No operation is
queued when no fresh worker heartbeat is present.
