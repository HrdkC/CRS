# CRS V13 Archive/Delete Recipe Code Autofill

## Scope

This patch updates the controlled recipe-retention confirmation screen.

## Changes

- Archive confirmation continues to prefill the selected recipe code.
- Permanent-delete confirmation now also prefills the selected archived recipe code.
- The prefilled recipe code is read-only and is still submitted for server-side identity validation.
- Permanent deletion still requires the operator to type `DELETE` and enter a deletion reason.
- Restore and other retention actions keep their existing manual confirmation behavior.

## Database / PLC impact

- No database migration.
- No PLC communication.
- No SMTP/email/OTP functionality.
