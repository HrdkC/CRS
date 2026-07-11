# CRS UI and UX Review

## Current Design Position

The application has a consistent Apollo violet visual language, compact status badges, workbench cards, route groups and responsive modules. Header density and table behavior have been iteratively improved. This pass added an accessible compact navigation drawer for narrow viewports without changing desktop navigation.

## Pass-One Improvements

- Mobile menu button has an accessible label and expanded state.
- Narrow layouts use a controlled drawer instead of oversized wrapped navigation buttons.
- Escape, resize and route selection close the drawer.
- External alert text is rendered as text, preventing layout and markup injection.
- Existing focus styles, skip link and accessibility preference controls were retained.

## Remaining Visual Validation

The browser connector was policy-blocked from opening the local CRS URL during this audit. Templates, CSS syntax, literal links and unauthenticated routes were validated programmatically, but pixel-level evidence is outstanding.

Required manual/browser evidence:

- Login at 1920x1080 and 1366x768.
- Dashboard with all role variants.
- Recipe editor, phase control, PLC buffer operations and import preview.
- PLC, user, machine, family, audit and configuration tables.
- Tablet and mobile header, drawer, forms, tables and footer.
- Keyboard-only navigation, visible focus, zoom to 200%, and error states.

## Design Standard

- Violet is the brand/action color, not the only information color.
- Green means confirmed/safe, amber means attention, red means blocked/destructive.
- Primary action appears once per task region.
- Dense engineering data uses compact tables with horizontal containment, not oversized cards.
- Help is contextual or tooltip based where persistent text would obstruct work.
- Dynamic content must not resize fixed controls or overlap the sticky header/footer.

Accessibility baseline: [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/).
