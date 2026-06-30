#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import http.server
import os
import socket
import socketserver
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Serve the CD-Center local page.")
    parser.add_argument("--port", type=int, default=8765, help="Preferred local port.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--open", action="store_true", help="Open the page in the default browser.")
    parser.add_argument("--no-scan", action="store_true", help="Skip the automatic local capability scan.")
    parser.add_argument("--scan-output", type=Path, default=repo_root / "capability-registry.local.json", help="Local registry output path.")
    return parser.parse_args()


def find_free_port(host: str, preferred: int) -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, preferred))
            return preferred
        except OSError:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])


def open_browser(url: str) -> None:
    commands = []
    if sys.platform == "darwin":
        commands.append(["open", url])
    commands.append(["xdg-open", url])
    commands.append(["python3", "-m", "webbrowser", url])
    for command in commands:
        try:
            subprocess.Popen(command)
            return
        except OSError:
            continue


def run_scan(repo_root: Path, output: Path) -> None:
    subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "scan_capabilities.py"), "--output", str(output), "--pretty"],
        cwd=repo_root,
        check=True,
    )


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    if not args.no_scan:
        run_scan(repo_root, args.scan_output)

    port = find_free_port(args.host, args.port)
    url = f"http://{args.host}:{port}/"

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer((args.host, port), handler) as server:
        print(f"CD-Center running at {url}")
        print("Use Ctrl+C to stop.")
        if args.open:
            open_browser(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
