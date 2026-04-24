1. Visual Identity & Brand
The Aesthetic: "Cyber-Audiophile" — A blend of high-contrast typography and deep, layered transparencies.

The Palette:

Background: Deep Space Void (#050508) with subtle radial gradients (Teal and Blue accents).

Primary Accent: Modern Teal (#14b8a6) used for success states, primary buttons, and progress indicators.

Surfaces: Glassmorphism using backdrop-blur(18px) and semi-transparent backgrounds (rgba(20, 24, 31, 0.7)).

Borders: Subtle white opacity (rgba(255, 255, 255, 0.08)).

Typography: Clean, geometric sans-serif (Inter) with heavy weights for headings to maintain readability through the glass effects.

2. Component Architecture
App Shell: Fixed glass sidebar and top header. Page content uses a cross-fading {#key $page.url} transition.

Custom Elements (Web Components): All external plugin UI must be encapsulated as Custom Elements (echosync-plugin-id). They do not use Shadow DOM so they can inherit global Tailwind variables.

Interaction Model:

Omnibar (Cmd+K): The primary navigation method for power users.

Physicality: Every button uses active:scale-95 to simulate a physical press.

Event Bus: Communication between isolated Web Components and the App Shell happens via native window events (e.g., es-toast).