# CRS V11.11-RC1 — Dark Theme + Live PLC Status Refresh Patch

## Scope

This patch applies to the approved V11.11-RC1 baseline. It does not include SMTP, email, OTP, or V11.12 functionality.

## Changes

- Completes dark-theme styling for Recipe PLC Buffer Operations.
- Replaces white/light page panels with readable dark surfaces.
- Corrects text contrast in live interlock cards, progress/history cards, and Machine / Stage PLC Tags.
- Separates PLC purpose, tag name, datatype, and array size so they do not overlap.
- Adds a read-only live-status JSON endpoint.
- Automatically reads the selected PLC interlock/handshake values every 2 seconds while the page is visible.
- Updates Actual, Expected, Healthy/Check/Readable, summary, connection state, issue list, and last-updated time without page reload.
- Adds Refresh Now and immediate refresh when the selected PLC changes.
- Prevents overlapping browser polling and pauses polling while the tab is hidden.
- Marks live-status polling as background traffic so it does not reset idle auto-logout.
- Uses no-store response headers.

## PLC safety

The automatic refresh performs PLC reads only through the existing `get_live_tag_status()` path. It does not write PLC values or start a recipe operation.

## Apply

Stop CRS, extract this ZIP over the current project root, allow file replacement, restart CRS, and press Ctrl+F5.

## Validation

- Python compile: passed
- JavaScript syntax: passed
- Jinja templates parsed: 62
- Complete safe suite: 49 passed
- Live endpoint test uses mocked PLC status; no real PLC connection/read/write was performed during patch validation
