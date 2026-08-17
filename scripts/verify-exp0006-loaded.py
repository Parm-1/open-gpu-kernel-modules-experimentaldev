#!/usr/bin/env python3
"""Verify an approved EXP-0006 build after its modules are loaded.

This verifier is read-only. It binds the approved manifest hash, staged module
hashes, running kernel, loaded module version/srcversion, and nvidia_drm probe
parameters into one structured result. It does not load, unload, or configure a
module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import tempfile
from pathlib import Path
from typing import Any

RUNTIME_MODULES = {
    "nvidia.ko": "nvidia",
    "nvidia-modeset.ko": "nvidia_modeset",
    "nvidia-drm.ko": "nvidia_drm",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_or_none(path: Path) -> str | None:
    try:
        return path.read_text(errors="replace").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def valid_sha256(value: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{64}", value) is not None


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    expected: Any,
    actual: Any,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "passed": passed,
            "expected": expected,
            "actual": actual,
        }
    )


def verify(
    manifest_path: Path,
    expected_manifest_sha256: str,
    expected_probe: str,
    sys_module_root: Path,
    kernel_release: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    manifest_path = manifest_path.resolve()
    build_dir = manifest_path.parent

    manifest_hash = sha256_file(manifest_path)
    add_check(
        checks,
        "manifest-sha256",
        manifest_hash == expected_manifest_sha256,
        expected_manifest_sha256,
        manifest_hash,
    )

    manifest = json.loads(manifest_path.read_text())
    add_check(
        checks,
        "kernel-release",
        manifest.get("kernel_release") == kernel_release,
        manifest.get("kernel_release"),
        kernel_release,
    )
    source = manifest.get("source")
    source_clean = isinstance(source, dict) and source.get("dirty") is False and bool(source.get("commit"))
    add_check(checks, "clean-source-manifest", source_clean, True, source_clean)
    cleanup = manifest.get("cleanup")
    cleanup_ok = (
        isinstance(cleanup, dict)
        and cleanup.get("preclean_returncode") == 0
        and cleanup.get("build_returncode") == 0
        and cleanup.get("postclean_returncode") == 0
        and cleanup.get("clean_tree_verified") is True
    )
    add_check(checks, "build-cleanup", cleanup_ok, True, cleanup_ok)

    module_records = {
        record.get("name"): record
        for record in manifest.get("modules", [])
        if isinstance(record, dict) and isinstance(record.get("name"), str)
    }
    for file_name, sys_name in RUNTIME_MODULES.items():
        record = module_records.get(file_name)
        add_check(checks, f"{sys_name}-manifest-record", record is not None, True, record is not None)
        if record is None:
            continue

        relative_path = record.get("relative_path")
        artifact_path = build_dir / str(relative_path)
        artifact_exists = artifact_path.is_file()
        add_check(checks, f"{sys_name}-artifact-exists", artifact_exists, True, artifact_exists)
        if artifact_exists:
            artifact_hash = sha256_file(artifact_path)
            add_check(
                checks,
                f"{sys_name}-artifact-sha256",
                artifact_hash == record.get("sha256"),
                record.get("sha256"),
                artifact_hash,
            )

        sys_dir = sys_module_root / sys_name
        loaded = sys_dir.is_dir()
        add_check(checks, f"{sys_name}-loaded", loaded, True, loaded)
        if not loaded:
            continue

        loaded_version = text_or_none(sys_dir / "version")
        add_check(
            checks,
            f"{sys_name}-version",
            loaded_version == record.get("version"),
            record.get("version"),
            loaded_version,
        )
        expected_srcversion = record.get("srcversion")
        loaded_srcversion = text_or_none(sys_dir / "srcversion")
        srcversion_comparable = bool(expected_srcversion and loaded_srcversion)
        add_check(
            checks,
            f"{sys_name}-srcversion-available",
            srcversion_comparable,
            True,
            srcversion_comparable,
        )
        if srcversion_comparable:
            add_check(
                checks,
                f"{sys_name}-srcversion",
                loaded_srcversion == expected_srcversion,
                expected_srcversion,
                loaded_srcversion,
            )

    modeset = text_or_none(sys_module_root / "nvidia_drm" / "parameters" / "modeset")
    add_check(checks, "nvidia-drm-modeset", modeset in {"Y", "1"}, "Y or 1", modeset)
    probe = text_or_none(sys_module_root / "nvidia_drm" / "parameters" / "hdcp_probe")
    add_check(checks, "nvidia-drm-hdcp-probe", probe == expected_probe, expected_probe, probe)

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": 1,
        "experiment": "EXP-0006-read-only-nvkms-hdcp",
        "passed": passed,
        "kernel_release": kernel_release,
        "manifest_sha256": manifest_hash,
        "expected_probe": expected_probe,
        "checks": checks,
        "claim_boundary": "Loaded-build identity and parameter evidence only; no HDCP capability or protection state is inferred.",
    }


def write_output(path: Path | None, result: dict[str, Any]) -> None:
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(text, end="")
        return
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.write_text(text)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        build_dir = root / "build"
        modules_dir = build_dir / "modules"
        sys_root = root / "sys-module"
        modules_dir.mkdir(parents=True)
        sys_root.mkdir()

        records: list[dict[str, Any]] = []
        for index, (file_name, sys_name) in enumerate(RUNTIME_MODULES.items(), start=1):
            artifact = modules_dir / file_name
            artifact.write_bytes(f"module-{index}".encode())
            srcversion = f"SRC{index}"
            records.append(
                {
                    "name": file_name,
                    "relative_path": f"modules/{file_name}",
                    "sha256": sha256_file(artifact),
                    "version": "610.57.04",
                    "srcversion": srcversion,
                }
            )
            module_dir = sys_root / sys_name
            (module_dir / "parameters").mkdir(parents=True)
            (module_dir / "version").write_text("610.57.04\n")
            (module_dir / "srcversion").write_text(srcversion + "\n")

        (sys_root / "nvidia_drm" / "parameters" / "modeset").write_text("Y\n")
        (sys_root / "nvidia_drm" / "parameters" / "hdcp_probe").write_text("Y\n")
        manifest = {
            "source": {"commit": "a" * 40, "dirty": False},
            "kernel_release": "6.8.0-test",
            "cleanup": {
                "preclean_returncode": 0,
                "build_returncode": 0,
                "postclean_returncode": 0,
                "clean_tree_verified": True,
            },
            "modules": records,
        }
        manifest_path = build_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        manifest_hash = sha256_file(manifest_path)
        result = verify(manifest_path, manifest_hash, "Y", sys_root, "6.8.0-test")
        assert result["passed"] is True

        (sys_root / "nvidia_drm" / "parameters" / "hdcp_probe").write_text("N\n")
        failed = verify(manifest_path, manifest_hash, "Y", sys_root, "6.8.0-test")
        assert failed["passed"] is False
        assert valid_sha256(manifest_hash)
    print("verify-exp0006-loaded self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expect-probe", choices=("Y", "N"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sys-module-root", type=Path, default=Path("/sys/module"))
    parser.add_argument("--kernel-release", default=platform.release())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.manifest is None or args.expected_manifest_sha256 is None or args.expect_probe is None:
        parser.error("--manifest, --expected-manifest-sha256, and --expect-probe are required")
    if not valid_sha256(args.expected_manifest_sha256):
        parser.error("--expected-manifest-sha256 must be 64 lowercase hexadecimal characters")
    result = verify(
        args.manifest,
        args.expected_manifest_sha256,
        args.expect_probe,
        args.sys_module_root,
        args.kernel_release,
    )
    write_output(args.output, result)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
