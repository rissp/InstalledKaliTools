#!/usr/bin/env python3
"""Generate an inventory of installed Kali Linux applications/tools with descriptions."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass
class PackageInfo:
    name: str
    version: str
    description: str


def run_command(command: list[str]) -> str:
    """Run a shell command and return stdout text."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command is not available: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{stderr}") from exc

    return result.stdout


def list_installed_packages() -> list[tuple[str, str]]:
    """Return (package, version) for installed packages via dpkg-query."""
    raw = run_command(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
    packages: list[tuple[str, str]] = []

    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            name, version = line.split("\t", 1)
        except ValueError:
            continue
        packages.append((name.strip(), version.strip()))

    return packages


def descriptions_for_packages(packages: Iterable[str]) -> dict[str, str]:
    """Fetch package descriptions in bulk using apt-cache show."""
    package_list = list(packages)
    if not package_list:
        return {}

    raw = run_command(["apt-cache", "show", *package_list])
    descriptions: dict[str, str] = {}

    current_package: str | None = None
    current_description: str | None = None

    for line in raw.splitlines():
        if line.startswith("Package: "):
            current_package = line.removeprefix("Package: ").strip()
            current_description = None
        elif line.startswith("Description: ") and current_package:
            current_description = line.removeprefix("Description: ").strip()
            if current_package not in descriptions:
                descriptions[current_package] = current_description
        elif line == "":
            current_package = None
            current_description = None

    return descriptions


def collect_inventory(limit: int | None = None) -> list[PackageInfo]:
    package_rows = list_installed_packages()
    if limit is not None:
        package_rows = package_rows[:limit]

    descriptions = descriptions_for_packages(name for name, _ in package_rows)

    return [
        PackageInfo(name=name, version=version, description=descriptions.get(name, "Description not available"))
        for name, version in package_rows
    ]


def write_json(inventory: list[PackageInfo], output_path: Path) -> None:
    output_path.write_text(json.dumps([asdict(item) for item in inventory], indent=2), encoding="utf-8")


def write_csv(inventory: list[PackageInfo], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "version", "description"])
        writer.writeheader()
        for item in inventory:
            writer.writerow(asdict(item))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a list of installed Kali Linux tools/applications and their descriptions."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output file format (default: json).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="kali_installed_tools.json",
        help="Output file path (default: kali_installed_tools.json).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional package limit for faster generation during testing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_path = Path(args.output)
    inventory = collect_inventory(limit=args.limit)

    if args.format == "json":
        write_json(inventory, output_path)
    else:
        write_csv(inventory, output_path)

    print(f"Generated inventory for {len(inventory)} packages at: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
