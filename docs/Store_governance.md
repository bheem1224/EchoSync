Planned EchoSync Plugin Store Governance Guidelines


🏛️ EchoSync Plugin Store Governance & Submission Guide
Welcome to the EchoSync-plugins repository! This repository acts as the central registry and home for all Official and Community plugins for the EchoSync platform.

EchoSync operates on a Zero-Trust Architecture powered by the Nexus Framework. We want this ecosystem to be a developer's dream—frictionless and open—without compromising the security and stability of our users' home labs.

This document outlines the rules for getting your plugin listed on the Official Store, how our automated sandbox works, and how our community moderation ("The Web of Trust") operates.

🛡️ 1. The Security Baseline
To protect users from malicious code, all plugins are evaluated by the EchoSync core AST (Abstract Syntax Tree) Scanner.

The Open Source Mandate: To be listed on the Official Store, your plugin must be open-source and hosted on a public repository (GitHub/GitLab). Pre-compiled native binaries without accessible source code are strictly banned.

The "Fast Track" (Sandboxed): If your plugin is written in pure Python, utilizes the plugin_SDK, and passes the AST Sandbox without requesting privileged_mode, it qualifies for the Fast Track. These plugins are automatically approved and merged by our CI/CD bot.

The "Audit Track" (Native/Privileged): If your plugin requests privileged_mode to bypass the AST, or includes native C/Rust .so/.dll files, it triggers a mandatory manual code audit.

Note on Rust: We strongly encourage developers to compile Rust plugins to WASM (.wasm) instead of native binaries. WASM plugins execute in a secure virtual machine, do not require privileged_mode, and qualify for the Fast Track.

✨ 2. Quality & Polish Standards
To keep the store highly functional, plugins must adhere to the following metadata and stability standards:

Strict Namespacing: Your plugin directory must perfectly match the {source}.{author}.{plugin_name} format (e.g., community.johndoe.spotify).

The Manifest: Your manifest.json must be 100% complete, including a clear description, relevant tags (e.g., metadata, scraper), a valid semantic version number, and a link to the source repository.

Graceful Failure: Plugins must handle API timeouts and network errors cleanly using sdk.logger. A plugin must never crash the core EchoSync event loop.

🕸️ 3. The "Web of Trust" (Community Moderation)
EchoSync is maintained by a small core team. To prevent bottlenecks in reviewing complex "Audit Track" plugins, we utilize a decentralized Web of Trust.

Tier 1: Verified Users
Who: Any user with a GitHub account older than 1 year or a history of valid contributions to EchoSync.

Role: Verified users can test Fast Track plugins and assign a [Community Verified] vouch to signal stability and usefulness to the broader community.

Tier 2: Nexus Sentinels
Who: Elite community developers. To become a Sentinel, you must have authored a Fast Track plugin that has been on the store for >60 days and received at least three [Community Verified] vouches.

Role: Sentinels have the authority to perform code audits on "Audit Track" (privileged) plugins.

The Rule of Multi-Sig: A privileged plugin requires the approval of two independent Nexus Sentinels before the bot will merge it.

The Slashing Condition: Sentinels stake their reputation on their audits. If a Sentinel approves a privileged plugin that is later found to contain malicious code, they permanently lose Sentinel status, and their own plugins are demoted.

### Tier 3: Nexus Vanguard (Core Maintainer)
* **Who:** The absolute elite of the EchoSync community. These are developers who have proven exceptional dedication not just to the plugin ecosystem, but to the core EchoSync engine itself.
* **Requirements to become a Vanguard:**
    1. Must have held Tier 2 (Nexus Sentinel) status in good standing for at least **60 days**.
    2. Must have successfully submitted and had merged at least **three (3) high-quality Pull Requests** directly into the *main* EchoSync core repository (e.g., bug fixes, core engine optimizations, SDK hook additions).
    3. Must be invited by or explicitly request access from the project lead.
* **Role & Power:** Vanguards are granted push/merge access to the main `EchoSync` repository. They help triage core engine bugs, merge community PRs, and shape the architectural roadmap of the platform.
* **The Failsafe:** While Vanguards have core write access, all merges to the `main` branch still require standard CI/CD checks (pytest passing). The project founder retains ultimate BDFL (Benevolent Dictator for Life) status to revoke access if a Vanguard merges unstable or malicious code to the core.

🧟 4. The Anti-Abandonware Protocol
We recognize that open-source developers have lives outside of code. However, dead plugins harm the ecosystem.

The 90-Day Rot: If a plugin fundamentally breaks (e.g., the target API changes) and the author does not respond to issues or submit a patch within 90 days, the plugin receives an [Abandoned] tag on the store.

Community Takeover: Because all plugins are open-source, if a plugin is tagged as Abandoned, any other developer is permitted to fork it, fix it, and submit a Pull Request to claim the namespace slot (redirecting the store listing to their maintained fork).

Pruning: Plugins that remain fundamentally broken and unclaimed for 6 months are automatically de-listed from the store UI.

🚀 5. How to Submit Your Plugin
We do not use a manual submission portal. The entire store is driven by Git automation.

Host Your Code: Ensure your plugin is pushed to a public GitHub/GitLab repository.

Update the Registry: Fork this repository (EchoSync-plugins) and add your repository's URL to the registry.json file.

Open a Pull Request: Submit your PR.

The Bot Takes Over: * Our GitHub Action will immediately download your repo, check your manifest.json, and run the AST Scanner.

If it passes the sandbox (Fast Track), the bot will automatically merge your PR! Your plugin will appear on the store within minutes.

If it requires privileged_mode (Audit Track), the bot will tag the PR with [Needs Audit] and ping the Nexus Sentinels for review.