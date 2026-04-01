#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Tool:
    command: str
    package: str
    version: str
    path: str


def run_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}): {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def get_installed_packages() -> dict[str, str]:
    output = run_cmd(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
    return dict(line.split("\t", 1) for line in output.splitlines() if "\t" in line)


def discover_commands(path_dirs: list[str]) -> dict[str, str]:
    commands: dict[str, str] = {}
    for directory in path_dirs:
        if not directory or not os.path.isdir(directory):
            continue
        try:
            for entry in os.scandir(directory):
                if entry.is_file(follow_symlinks=True) and os.access(entry.path, os.X_OK):
                    commands.setdefault(entry.name, entry.path)
        except PermissionError:
            continue
    return commands


def chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def package_index_for_paths(paths: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for batch in chunks(paths, 200):
        proc = subprocess.run(["dpkg", "-S", *batch], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        for line in proc.stdout.splitlines():
            if ":" not in line:
                continue
            pkg, path = line.split(":", 1)
            mapping[path.strip()] = pkg.strip()
    return mapping


def build_catalog(include_regex: str, exclude_regex: str | None, limit: int | None) -> list[Tool]:
    include_pattern = re.compile(include_regex)
    exclude_pattern = re.compile(exclude_regex) if exclude_regex else None

    installed = get_installed_packages()
    commands = discover_commands(os.environ.get("PATH", "").split(":"))
    path_to_pkg = package_index_for_paths(list(commands.values()))

    catalog: list[Tool] = []
    for command, command_path in sorted(commands.items()):
        package = path_to_pkg.get(command_path)
        if not package or package not in installed:
            continue
        if not include_pattern.search(package):
            continue
        if exclude_pattern and exclude_pattern.search(package):
            continue

        catalog.append(Tool(command=command, package=package, version=installed[package].strip(), path=command_path))
        if limit is not None and len(catalog) >= limit:
            break

    return catalog


def to_json(tools: Iterable[Tool]) -> str:
    return json.dumps([asdict(t) for t in tools], indent=2, ensure_ascii=False)


def to_csv(tools: Iterable[Tool]) -> str:
    from io import StringIO

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["command", "package", "version", "path"])
    writer.writeheader()
    for tool in tools:
        writer.writerow(asdict(tool))
    return output.getvalue()


def to_markdown(tools: Iterable[Tool]) -> str:
    lines = ["# Installed Kali Tools Catalog", "", "| Command | Package | Version | Path |", "|---|---|---|---|"]
    for tool in tools:
        lines.append(f"| `{tool.command}` | `{tool.package}` | `{tool.version}` | `{tool.path}` |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Catalog locally installed Kali tools")
    parser.add_argument("--format", choices=("json", "csv", "md"), default="json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-package", default=r".*", help="Regex for package names to include")
    parser.add_argument("--exclude-package")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        tools = build_catalog(args.include_package, args.exclude_package, args.limit)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rendered = to_json(tools) if args.format == "json" else to_csv(tools) if args.format == "csv" else to_markdown(tools)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered if rendered.endswith("\n") else rendered + "\n")

    print(f"Catalog contains {len(tools)} installed tools.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
