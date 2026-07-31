# UX research decisions

Sources reviewed on 2026-07-22:

- GOV.UK Design System task list: https://design-system.service.gov.uk/components/task-list/
- IBM Carbon progress indicator: https://carbondesignsystem.com/components/progress-indicator/usage/
- W3C WCAG 2.2 focus order: https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html
- W3C WCAG 2.2 reflow: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- W3C WCAG 2.2 status messages: https://www.w3.org/WAI/WCAG22/Understanding/status-messages

Applied decisions:

- Use a vertical progress indicator for the seven-step linear journey.
- Make the full step row selectable and show completed, current, blocked, and attention states in text.
- Save the current position so users can resume later.
- Validate completion from domain data rather than allowing users to mark steps complete manually.
- Keep DOM and visual order aligned for keyboard users.
- Reflow the step list horizontally at tablet width and stack content at mobile width.
- Use `role=status` for changing attention messages and semantic `role=progressbar` for overall progress.
- Keep raw engineering controls outside the standard operator-oriented journey.

