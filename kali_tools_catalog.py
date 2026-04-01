#!/usr/bin/env python3
"""Generate a simple catalog of installed Kali tools."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a catalog of tools available in PATH.",
    )
    parser.add_argument(
        "--tools",
        nargs="*",
        default=["nmap", "sqlmap", "hydra", "nikto", "john", "aircrack-ng"],
        help="Tool names to check (default: common Kali tools).",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file path. Prints to stdout when omitted.",
    )
    return parser.parse_args()


def collect_tools(tools: Iterable[str]) -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    for tool in tools:
        path = shutil.which(tool)
        rows.append(
            {
                "tool": tool,
                "installed": bool(path),
                "path": path or "",
            }
        )
    return rows


def render_table(rows: list[dict[str, str | bool]]) -> str:
    if not rows:
        return "No tools requested."

    tool_width = max(len("Tool"), *(len(str(r["tool"])) for r in rows))
    status_width = len("Installed")
    lines = [
        f"{'Tool':<{tool_width}}  {'Installed':<{status_width}}  Path",
        f"{'-' * tool_width}  {'-' * status_width}  {'-' * 30}",
    ]
    for row in rows:
        installed = "yes" if row["installed"] else "no"
        lines.append(f"{row['tool']:<{tool_width}}  {installed:<{status_width}}  {row['path']}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    rows = collect_tools(args.tools)

    if args.format == "json":
        rendered = json.dumps(rows, indent=2)
    else:
        rendered = render_table(rows)

    if args.output:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
