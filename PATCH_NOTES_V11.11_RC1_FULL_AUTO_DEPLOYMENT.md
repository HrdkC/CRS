# CRS V11.11-RC1 Full Automatic Deployment Patch

This patch removes the operational requirement to start a separate BAT file or
manually run `scripts/run_plc_worker.py`.

## Runtime behavior

Starting `python app.py` now automatically:

1. starts exactly one durable PLC worker as a hidden child process;
2. waits for the worker heartbeat before serving the website;
3. monitors the worker continuously;
4. restarts it automatically after an unexpected exit;
5. prevents duplicate fresh workers through the existing singleton guard;
6. stops the child worker when CRS shuts down normally;
7. uses Waitress automatically when `CRS_DEPLOYMENT_MODE=production`.

The PLC worker remains a separate process, so PLC jobs are still durable and do
not run inside Flask request threads.

## Windows automatic startup

Run once from an elevated PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_crs_autostart_task.ps1
```

The installer registers a SYSTEM scheduled task that starts CRS automatically
30 seconds after Windows startup and restarts it after failure. There is no
operator confirmation and no BAT file is required.

Remove it with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_crs_autostart_task.ps1
```

## Configuration

- `CRS_AUTO_START_PLC_WORKER=1` (default): automatic worker supervision.
- `CRS_AUTO_START_PLC_WORKER=0`: maintenance/web-only mode.
- `CRS_PLC_WORKER_POLL_SECONDS=0.25`: queue pickup interval.
- `CRS_PLC_WORKER_MAX_RESTARTS=5`: restart attempts before requiring review.
- `CRS_DEPLOYMENT_MODE=production`: use Waitress.

No SMTP, email, OTP, or V11.12 functionality is included.
