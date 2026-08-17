#!/usr/bin/env python3
"""Render a non-executing, machine-specific EXP-0006 rollback plan."""
from __future__ import annotations

import argparse
import json
import shlex
import tempfile
from pathlib import Path
from typing import Any

REQUIRED_MODULES = ("nvidia", "nvidia_modeset", "nvidia_drm")
OPTIONAL_MODULES = ("nvidia_uvm", "nvidia_peermem")


def module_by_name(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for item in snapshot.get("modules", []):
        name = item.get("name")
        if isinstance(name, str):
            records[name] = item
    return records


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = module_by_name(snapshot)
    for name in REQUIRED_MODULES:
        record = records.get(name)
        if record is None:
            errors.append(f"missing module record: {name}")
            continue
        for field in ("filename", "sha256", "version", "vermagic"):
            if not record.get(field):
                errors.append(f"{name}: missing {field}")
    return errors


def render(snapshot: dict[str, Any]) -> str:
    errors = validate_snapshot(snapshot)
    if errors:
        raise ValueError("invalid snapshot: " + "; ".join(errors))
    records = module_by_name(snapshot)
    expected = snapshot.get("expected_version", "unknown")
    loaded_optional = [name for name in OPTIONAL_MODULES if records.get(name, {}).get("loaded")]

    lines = [
        "# EXP-0006 machine-specific rollback plan",
        "",
        "> This document does not execute anything. Review it offline before module-load approval.",
        "",
        f"Expected known-good NVIDIA version: `{expected}`",
        "",
        "## Known-good module identity",
        "",
        "| Module | Loaded at snapshot | Path | SHA-256 | Version | Vermagic |",
        "|---|---:|---|---|---|---|",
    ]
    for name in REQUIRED_MODULES + OPTIONAL_MODULES:
        record = records.get(name)
        if record is None:
            continue
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                name,
                "yes" if record.get("loaded") else "no",
                record.get("filename") or "unavailable",
                record.get("sha256") or "unavailable",
                record.get("version") or "unavailable",
                record.get("vermagic") or "unavailable",
            )
        )

    unload_order = ["nvidia_drm", "nvidia_modeset", *loaded_optional, "nvidia"]
    load_order = ["nvidia", "nvidia_modeset", *loaded_optional, "nvidia_drm"]
    lines.extend(
        [
            "",
            "## Intended recovery sequence",
            "",
            "Run only from a working SSH or local TTY session after the graphical session is stopped. Never use force-removal.",
            "",
            "```bash",
            "set -euo pipefail",
            "sudo systemctl isolate multi-user.target",
            "sudo modprobe -r " + " ".join(unload_order),
        ]
    )
    for name in load_order:
        lines.append("sudo modprobe " + shlex.quote(name))
    lines.extend(
        [
            "",
            "# Verify that modprobe selected the recorded known-good files, hashes, and version.",
        ]
    )
    for name in REQUIRED_MODULES:
        expected_path = records[name]["filename"]
        expected_hash = records[name]["sha256"]
        lines.append(f"test \"$(modinfo -n {shlex.quote(name)})\" = {shlex.quote(str(expected_path))}")
        lines.append(
            f"test \"$(sha256sum \"$(modinfo -n {shlex.quote(name)})\" | awk '{{print $1}}')\" = {shlex.quote(str(expected_hash))}"
        )
    lines.extend(
        [
            f"test \"$(cat /sys/module/nvidia/version)\" = {shlex.quote(str(expected))}",
            "sudo systemctl isolate graphical.target",
            "```",
            "",
            "If an unload, load, path, hash, or version check fails, remain in text mode and use the independently tested known-good boot entry. Do not force a module operation and do not continue the experiment.",
            "",
            "## Pre-execution manual checks",
            "",
            "- [ ] This plan is stored offline on a second device.",
            "- [ ] SSH and local TTY access were tested in the current boot.",
            "- [ ] The known-good boot entry was tested.",
            "- [ ] The module paths and hashes above still match the filesystem.",
            "- [ ] Explicit approval covers unload, local `insmod`, restoration, and any reboot.",
            "",
        ]
    )
    return "\n".join(lines)


def self_test() -> None:
    snapshot = {
        "expected_version": "610.57.04",
        "modules": [
            {"name": "nvidia", "filename": "/lib/nvidia.ko", "sha256": "a" * 64, "version": "610.57.04", "vermagic": "k", "loaded": True},
            {"name": "nvidia_modeset", "filename": "/lib/nvidia-modeset.ko", "sha256": "b" * 64, "version": "610.57.04", "vermagic": "k", "loaded": True},
            {"name": "nvidia_drm", "filename": "/lib/nvidia-drm.ko", "sha256": "c" * 64, "version": "610.57.04", "vermagic": "k", "loaded": True},
            {"name": "nvidia_uvm", "filename": "/lib/nvidia-uvm.ko", "sha256": "d" * 64, "version": "610.57.04", "vermagic": "k", "loaded": True},
        ],
    }
    text = render(snapshot)
    assert "modprobe -r nvidia_drm nvidia_modeset nvidia_uvm nvidia" in text
    assert "modinfo -n nvidia_drm" in text
    assert "sha256sum" in text
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "snapshot.json"
        path.write_text(json.dumps(snapshot))
        assert validate_snapshot(json.loads(path.read_text())) == []
    print("render-exp0006-rollback self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.snapshot is None:
        parser.error("snapshot is required unless --self-test is used")
    snapshot = json.loads(args.snapshot.read_text())
    output = render(snapshot)
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite {args.output}")
        args.output.write_text(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
