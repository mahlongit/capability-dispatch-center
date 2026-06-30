#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local HTML gallery for design-md templates.")
    parser.add_argument("--source", type=Path, default=Path.home() / ".local" / "share" / "awesome-design-md" / "design-md")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=24)
    return parser.parse_args()


def summarize_template(path: Path) -> tuple[str, str]:
    readme = path / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return path.name, line[:180]
    return path.name, f"Local template {path.name}"


def build_card(name: str, description: str) -> str:
    slug = html.escape(name)
    desc = html.escape(description)
    return f"""
      <article class="card">
        <div class="badge">{slug[:3].upper()}</div>
        <h2>{slug}</h2>
        <p>{desc}</p>
      </article>
    """


def main() -> int:
    args = parse_args()
    templates = [candidate for candidate in sorted(args.source.iterdir()) if candidate.is_dir() and not candidate.name.startswith(".")]
    cards = []
    for candidate in templates[: args.limit]:
        name, description = summarize_template(candidate)
        cards.append(build_card(name, description))

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>design-md 模板画廊</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --panel: rgba(255,255,255,.92);
      --ink: #152033;
      --muted: #62708a;
      --line: #d8e0ee;
      --accent: #4d6cf0;
      --accent-2: #152033;
      --shadow: 0 20px 50px rgba(35, 56, 98, .12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 15px/1.6 -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(77,108,240,.16), transparent 26%),
        linear-gradient(180deg, #f6f8fc 0%, #edf2fb 100%);
    }}
    .shell {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 40px 28px 64px;
    }}
    .hero {{
      margin-bottom: 28px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font: 700 40px/1.05 Georgia, serif;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 780px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }}
    .card {{
      min-height: 220px;
      padding: 22px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
    }}
    .badge {{
      width: 44px;
      height: 44px;
      display: grid;
      place-items: center;
      border-radius: 14px;
      margin-bottom: 18px;
      color: white;
      font-weight: 700;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }}
    .card h2 {{
      margin: 0 0 8px;
      font: 700 24px/1.15 Georgia, serif;
      letter-spacing: 0;
    }}
    .card p {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>design-md 模板画廊</h1>
      <p>本地模板预览页。这里展示已安装模板的名称和摘要，便于先选风格方向，再决定安装到具体项目。</p>
    </section>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_doc, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
