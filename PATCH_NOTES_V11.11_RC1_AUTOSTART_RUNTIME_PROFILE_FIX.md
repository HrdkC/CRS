# V11.11-RC1 Automatic Startup Runtime Profile Fix

## Root cause

The scheduled runner forced `CRS_DEPLOYMENT_MODE=production`. The CRS application
correctly fails closed in production unless production security prerequisites are
configured, including a persistent secret, secure cookies, and trusted hosts.
The current HTTP trial deployment had not completed those HTTPS/security steps,
so the scheduled task exited with result `1` before opening port 5000.

## Fix

- Separates HTTP server selection from the security profile.
- Scheduled startup uses Waitress automatically without falsely declaring the
  current HTTP installation to be production-secure.
- Keeps `CRS_DEPLOYMENT_MODE=development` by default for the current HTTP setup.
- Uses `CRS_USE_WAITRESS=1` to run the production-grade WSGI server.
- Continues to start and supervise the durable PLC worker automatically.
- Adds startup diagnostics in `logs/crs_autostart.log`.
- Prevents duplicate scheduled-task instances.
- Registers pytest markers to remove the `pytest.mark.safe` warning.

## Security boundary

This fixes automatic process startup. It does not declare the current HTTP
installation production-secure. Switch to `CRS_DEPLOYMENT_MODE=production` only
after HTTPS, secure cookies, trusted hosts and machine-level secret configuration
are commissioned.
