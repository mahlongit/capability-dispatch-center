# Install

CD-Center supports three entry paths:

## 1. Prompt Only

Use the prompt in [PROMPTS.md](PROMPTS.md) with your AI tool. This is the lowest-friction path.

## 2. Terminal Install

```bash
git clone https://github.com/mahlongit/capability-dispatch-center
cd capability-dispatch-center
bash scripts/install.sh
```

After that:

```bash
cd-center doctor
cd-center scan
cd-center open
```

## 3. Manual Local Page

Without installing the launcher:

```bash
python3 scripts/scan_capabilities.py
python3 scripts/serve.py --open
```

## Requirements

- `python3`
- `bash`
- A local browser

No Node-based build step is required for the core page.
