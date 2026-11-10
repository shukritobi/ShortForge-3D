"""Versioned ShortForge asset and animation registry validation.

This metadata catalog is the seed for a future independent asset package.
The current procedural builders still live in the water-tower script.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"^[a-z]+[.][a-z][a-z0-9_]+$")
VERSION = re.compile(r"^[0-9]+[.][0-9]+[.][0-9]+$")
KINDS = {"environment", "model", "action", "camera", "material", "sfx"}
STATUSES = {"prototype", "validated", "deprecated"}


def load_catalog(path: str | Path = ROOT / "assets" / "catalog.json") -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("catalog_version") != 1:
        raise ValueError("Unknown asset catalog version")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Asset catalog is empty")
    keys = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Catalog entry must be an object")
        asset_id = entry.get("id")
        version = entry.get("version")
        if not isinstance(asset_id, str) or not ID.fullmatch(asset_id):
            raise ValueError(f"Bad asset ID: {asset_id}")
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise ValueError(f"Bad semantic version for {asset_id}")
        if entry.get("kind") not in KINDS or entry.get("status") not in STATUSES:
            raise ValueError(f"Unknown kind/status for {asset_id}")
        if not isinstance(entry.get("license"), str) or not entry["license"]:
            raise ValueError(f"Missing asset license: {asset_id}")
        source = entry.get("source")
        if not isinstance(source, str):
            raise ValueError(f"Missing source: {asset_id}")
        resolved = (ROOT / source).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.is_file():
            raise ValueError(f"Asset source is unavailable or outside repository: {source}")
        key = (asset_id, version)
        if key in keys:
            raise ValueError(f"Duplicate asset version: {asset_id}@{version}")
        keys.add(key)
    return data
