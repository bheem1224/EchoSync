# WebUI Design System & Svelte 5 Invariants

**Status:** Mandatory for all frontend autonomous execution.
**Objective:** Maintain a premium, consistent, and highly modular Svelte 5 frontend. Prevent styling drift, native HTML element clashes, and Svelte 4 syntax regressions.

## 1. Svelte 5 Exclusivity
- **Rule:** All new components MUST be written using Svelte 5 syntax (Runes: `$state`, `$derived`, `$props`, `$effect`, and snippets).
- **The "Boy Scout" Rule (Progressive Modernization):** Do not retroactively rewrite the entire UI. However, if you are tasked with updating an older Svelte 4 component, you may modernize that specific component to Svelte 5 *only* if it can be done safely without breaking its parent/child contracts.

## 2. Component Modularity & Extensibility
- **Rule:** Stick to reusable, mountable, and swappable web components. 
- **Dynamic Layouts:** Assume pages are highly customizable. Most dynamic views (dashboards) are driven by Home Assistant style YAML configurations.
- **Plugin Integration:** Plugins inject their settings and custom views via `ui_manifest.json`. Build components that gracefully accept slotted content or dynamic props from these manifests.
- **Fixed Pages:** The Sync, Library, and Task Manager pages are structurally fixed but still rely on the shared component library.

## 3. Styling & Thematic Consistency
- **Rule:** Do NOT use raw native HTML form elements (like `<select>`, `<input type="file">`) that rely on browser-default styling. This causes severe visual clashes against the dark theme. Always use or build custom UI components.
- **Color Palette:** Use the established CSS variables for the global theme (dark mode, teal/cyan accents, card-based layouts). Never hardcode hex values if a CSS variable exists.
- **Responsiveness:** The UI must be mobile-friendly, but NEVER compromise the density or power of the desktop experience to achieve it.

## 4. Interaction & UX Philosophy (The "Premium Web3" Feel)
- **Feedback:** Utilize Toast notifications and Pop-ups heavily for async states, errors, and confirmations.
- **Context Menus:** Hijack right-mouse clicks to open custom overflow/context menus on tracks, albums, and task items. 
- **Animations:** Use Svelte transitions (`fade`, `slide`, `fly`) when elements enter/leave the DOM to add a premium, smooth feel. Do not over-animate; use it purposefully.
- **Information Density:** Avoid extreme minimalism, but do not cram every feature into a single view. Elements must have a distinct purpose and function. Use tabs, slide-overs, and pop-ups to manage secondary information.