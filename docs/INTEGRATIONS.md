# Integrations

CD-Center is designed to sit above the execution tool, not replace it.

## Supported Tooling Styles

| Tool | Current Support | Usage |
|---|---|---|
| Codex / CDX | direct | Prompt-based routing, local scan, local page |
| Claude Code | direct | Prompt-based routing, local scan, local page |
| Cursor | direct | Prompt-based routing, local scan, local page |
| GitHub Copilot | direct | Prompt-based routing, local scan, local page |
| OpenClaw | direct | Prompt-based routing, local scan, local page |
| Hermes Agent | direct | Prompt-based routing, local scan, local page |
| Qoder | direct | Prompt-based routing, local scan, local page |
| Trae | direct | Prompt-based routing, local scan, local page |

## Integration Modes

1. Prompt mode:
   The user gives the CD-Center prompt to the AI tool and asks it to scan first, route second, execute third.

2. Launcher mode:
   The user installs `cd-center` locally, runs `cd-center scan`, then opens the page with `cd-center open`.

3. Embedded page mode:
   The user opens the generated local page while working in another AI tool and copies the recommended prompt from the right-hand panel.

## Current Boundary

The project does not yet auto-install rules, skills, or agents into every ecosystem. It provides a discovery and routing layer that fits across multiple ecosystems with the same local scan result.
