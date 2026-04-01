# Kali Installed Tools Catalog

This project provides a small Kali Linux application that creates a list of installed packages/tools and writes a short description for each one.

## Requirements

- Kali Linux (or any Debian-based distro with `dpkg-query`)
- Python 3.10+

## Usage

Generate JSON output (default):

```bash
python3 kali_tools_catalog.py
```

Generate CSV output:

```bash
python3 kali_tools_catalog.py --format csv --output kali_tools.csv
```

Generate a small sample for quick checks:

```bash
python3 kali_tools_catalog.py --limit 25 --output sample.json
```

## Output fields

Each record contains:

- `name`: Package/tool name
- `version`: Installed package version
- `description`: Installed package short description from `dpkg-query`
