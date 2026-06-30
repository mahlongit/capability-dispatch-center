# Integrations

CD-Center is designed to sit above the execution tool, not replace it.

## Supported Tooling Styles

| Tool | Current Support | Usage |
|---|---|---|
| Codex / CDX | stub + page | project agent stub + local page |
| Claude Code | stub + page | global agent stub + local page |
| Cursor | stub + page | project rule stub + local page |
| GitHub Copilot | stub + page | global agent stub + local page |
| OpenClaw | stub + page | global skill stub + local page |
| Hermes Agent | stub + page | global skill stub + local page |
| Qoder | stub + page | global agent stub + local page |
| Trae | stub + page | project rule stub + local page |

## Integration Modes

1. Prompt mode:
   The user gives the CD-Center prompt to the AI tool and asks it to scan first, route second, execute third.

2. Launcher mode:
   The user installs `cd-center` locally, runs `cd-center scan`, then opens the page with `cd-center open`.

3. Embedded page mode:
   The user opens the generated local page while working in another AI tool and copies the recommended prompt from the right-hand panel.

## Current Boundary

The project now writes minimal integration stubs for common hosts through `scripts/install.sh`. These stubs are intentionally thin: they tell the host to route through CD-Center first. They do not replace the host's own execution model.
