# EchoSync Design & Architecture Blueprint

## 1. Visual Identity & Brand
* **The Aesthetic:** "Cyber-Audiophile" — High-contrast typography and deep, layered transparencies.
* **The Palette:**
  * Background: Deep Space Void (`#050508`) with subtle radial gradients.
  * Primary Accent: Modern Teal (`#14b8a6`) for success states and primary buttons.
  * Surfaces: Glassmorphism using `backdrop-blur(18px)` and `rgba(20, 24, 31, 0.7)`.
  * Borders: Subtle white opacity (`rgba(255, 255, 255, 0.08)`).
* **Interaction Model:** `Cmd+K` Omnibar for navigation, `active:scale-95` on all buttons for physical feel, and a Global `window` Event Bus for Toast notifications.

## 2. Core Functional Architecture
EchoSync strictly separates background analysis (Proposals) from active file operations (Execution).

### Suggestion Service (The Brain & Proposer)
* **Role:** Background Analytics & User Requests.
* **Logic:** Monitors listen counts, trends, and user request queues.
* **Limitations:** It has **ZERO** power to delete or modify the active library. Its only independent capability is downloading tracks strictly for ephemeral daily playlists.
* **Outputs:** It posts "Intents" (e.g., Upgrade Request, Delete Unpopular Track) to the Media Manager's queue.

### Media Manager (The Gatekeeper & Executor)
* **Role:** The ultimate authority on the file system.
* **Logic:** Executes destructive or transformative operations (Deletes, Moves, Upgrades).
* **UI/Admin:** Hosts the Dual-Queue Dashboard. All Intents from the Suggestion Service land in "Suggestions & Requests" waiting for Admin approval. Once approved (or caught by an auto-approve timing toggle), they move to "Pending Actions" for execution.
