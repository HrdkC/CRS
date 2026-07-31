# Accessibility review

Implemented checks:

- page title and one task-focused H1;
- semantic `nav` with `aria-current=step`;
- semantic progressbar with numeric value;
- text labels for every status and icon;
- source order matches visual order;
- native links, buttons, selects, and inputs;
- field labels and required attributes;
- attention summary announced with `role=status`;
- mobile reflow at 900 px and 640 px;
- dark-theme surfaces and explicit text colors;
- no viewport-scaled fonts or negative letter spacing;
- reduced-motion behavior inherits the existing application preference module.

Target acceptance still required:

- keyboard-only walkthrough;
- 200% browser zoom;
- forced-colors/high-contrast mode;
- light, dark, and system theme screenshots;
- authenticated viewport checks at 1920x1080, 1600x900, 1366x768, 1024x768, 768x1024, and 390x844.

