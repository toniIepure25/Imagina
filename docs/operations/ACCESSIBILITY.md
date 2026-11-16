# Accessibility status

**Status:** partially verified. No automated axe/WCAG gate is wired yet.

## Implemented

- Keyboard-operable Studio surfaces and command palette.
- Visible focus styles in the design system.
- Semantic headings and named links on the public landing.
- Reduced-motion preference respected in scene surfaces (verify per route).
- No color-only status in the claim/evidence badges.

## Gaps

- No automated `@axe-core/playwright` check.
- No screen-reader walkthrough recorded.
- No formal WCAG 2.2 AA audit.
- Contrast not measured across every route.
- The 3D stage is not fully operable without a pointer; the Structure view is the keyboard path.

## Next gate

1. Add `@axe-core/playwright` and run it on `/`, `/animus`, `/animus/[sessionId]`, and `/science`.
2. Record a screen-reader pass for the Studio and the measurement report.
3. Measure contrast and focus order on every primary route.
4. Publish a VPAT-style statement only after the audit.

Do not claim WCAG conformance before step 1–3 are complete.
