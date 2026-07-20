# CRS security and secret rotation checklist

The original workstation ZIP contained runtime and operational material. Treat any secret or shared credential that existed inside that archive as exposed until rotated.

## Required owner actions

- [ ] Restrict the GitHub repository if public access is not explicitly approved.
- [ ] Rotate `CRS_SECRET_KEY` and retire the old secret after active sessions are closed.
- [ ] Reset all seeded/default/temporary user passwords through an approved administrator flow.
- [ ] Rotate database credentials stored in any local profile or environment file.
- [ ] Review and rotate any PLC credential if one was ever stored beside the project.
- [ ] Remove old workstation ZIPs from shared folders and uncontrolled media.
- [ ] Preserve one encrypted evidence backup under restricted access.
- [ ] Run a history secret scan before any public or external repository use.
- [ ] Review the proposed Git history cleanup before any force-push.

Never paste actual secret values into tickets, reports, chat, commits, or release manifests.
