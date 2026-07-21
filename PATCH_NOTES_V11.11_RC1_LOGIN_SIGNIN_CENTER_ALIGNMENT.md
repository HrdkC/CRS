# CRS V11.11-RC1 — Login Sign-In Center Alignment Patch

## Scope

This patch applies to the approved V11.11-RC1 baseline with the responsive-header and guided-parameter-template patches already applied.

It does not include SMTP, email registration, OTP recovery, or V11.12 functionality.

## Changes

- Centers the complete sign-in form card inside the right-side login panel.
- Centers the username/password field stack within the form card.
- Centers the Sign In button horizontally.
- Centers the visible `Sign In` text inside the button.
- Preserves responsive behavior on narrow screens.
- Updates the production CSS bundle and browser cache version.

## Apply

1. Stop CRS.
2. Extract this ZIP over the CRS project root.
3. Allow replacement of existing files.
4. Restart CRS.
5. Press `Ctrl + F5` on the login page.

## Test

```powershell
python -m pytest -q tests/safe/test_login_signin_center_alignment.py tests/safe/test_responsive_header_reflow.py
python scripts/build_css_bundle.py --check
```

Expected result: `2 passed` and `CSS bundle is current`.
