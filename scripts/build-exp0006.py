#!/usr/bin/env python3
"""Build and stage EXP-0006 modules for the exact running kernel.

The tool is deliberately build-only: it never installs, unloads, loads, signs
unless explicit signing inputs are supplied, changes boot configuration, or
reboots. It emits a manifest and hashes suitable for the recovery review.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

EXPECTED_VERSION = "610.57.04"
MODULE_PATHS = (
    "kernel-open/nvidia.ko",
    "kernel-open/nvidia-modeset.ko",
    "kernel-open/nvidia-drm.ko",
    "kernel-open/nvidia-uvm.ko",
    "kernel-open/nvidia-peermem.ko",
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_version_mk(path: Path) -> str:
    text = path.read_text(errors="strict")
    match = re.search(r"^NVIDIA_VERSION\s*=\s*([^\s#]+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"unable to parse NVIDIA_VERSION from {path}")
    return match.group(1)


def vermagic_matches(vermagic: str, kernel_release: str) -> bool:
    return vermagic.strip().split(maxsplit=1)[0] == kernel_release


def run(argv: Sequence[str], *, cwd: Path, stdout_path: Path | None = None, stderr_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    if stdout_path is None or stderr_path is None:
        return subprocess.run(
            list(argv), cwd=cwd, check=False, capture_output=True, text=True,
            env={**os.environ, "LC_ALL": "C"},
        )
    with stdout_path.open("w") as stdout_stream, stderr_path.open("w") as stderr_stream:
        return subprocess.run(
            list(argv), cwd=cwd, check=False, stdout=stdout_stream, stderr=stderr_stream,
            text=True, env={**os.environ, "LC_ALL": "C"},
        )


def command_output(argv: Sequence[str], *, cwd: Path) -> str:
    result = run(argv, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {shlex.join(argv)}\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def git_metadata(repo_root: Path) -> dict[str, Any]:
    head = run(["git", "rev-parse", "HEAD"], cwd=repo_root)
    status = run(["git", "status", "--porcelain"], cwd=repo_root)
    return {
        "commit": head.stdout.strip() if head.returncode == 0 else None,
        "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def sign_module(module: Path, kernel_build: Path, key: Path, certificate: Path, repo_root: Path) -> None:
    sign_file = kernel_build / "scripts" / "sign-file"
    if not sign_file.is_file():
        raise RuntimeError(f"kernel sign-file helper not found: {sign_file}")
    result = run([str(sign_file), "sha256", str(key), str(certificate), str(module)], cwd=repo_root)
    if result.returncode != 0:
        raise RuntimeError(f"module signing failed for {module}: {result.stderr.strip()}")


def module_metadata(module: Path, kernel_release: str, expected_version: str, repo_root: Path) -> dict[str, Any]:
    version = command_output(["modinfo", "-F", "version", str(module)], cwd=repo_root)
    vermagic = command_output(["modinfo", "-F", "vermagic", str(module)], cwd=repo_root)
    signer = command_output(["modinfo", "-F", "signer", str(module)], cwd=repo_root)
    if version != expected_version:
        raise RuntimeError(f"{module}: version {version!r} does not match {expected_version!r}")
    if not vermagic_matches(vermagic, kernel_release):
        raise RuntimeError(f"{module}: vermagic {vermagic!r} does not match kernel {kernel_release!r}")
    return {
        "name": module.name,
        "relative_path": f"modules/{module.name}",
        "size": module.stat().st_size,
        "sha256": sha256_file(module),
        "version": version,
        "vermagic": vermagic,
        "signer": signer or None,
    }


def write_hashes(output_dir: Path) -> None:
    lines: list[str] = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "artifacts.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(output_dir)}")
    (output_dir / "artifacts.sha256").write_text("\n".join(lines) + "\n")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        version_mk = root / "version.mk"
        version_mk.write_text("NVIDIA_VERSION = 610.57.04\nNVIDIA_NVID_VERSION = 610.57.04\n")
        assert parse_version_mk(version_mk) == EXPECTED_VERSION
        sample = root / "sample"
        sample.write_bytes(b"abc")
        assert sha256_file(sample) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert vermagic_matches("6.8.0-137-generic SMP preempt mod_unload", "6.8.0-137-generic")
    assert not vermagic_matches("6.8.0-136-generic SMP", "6.8.0-137-generic")
    print("build-exp0006 self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--kernel-release", default=platform.release())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--jobs", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    parser.add_argument("--expected-version", default=EXPECTED_VERSION)
    parser.add_argument("--sign-key", type=Path)
    parser.add_argument("--sign-cert", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if (args.sign_key is None) != (args.sign_cert is None):
        parser.error("--sign-key and --sign-cert must be supplied together")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    repo_root = args.repo_root.resolve()
    kernel_build = Path("/lib/modules") / args.kernel_release / "build"
    output_dir = args.output_dir or repo_root / "artifacts" / f"EXP-0006-build-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    source_version = parse_version_mk(repo_root / "version.mk")
    if source_version != args.expected_version:
        raise SystemExit(f"source version {source_version} does not match pinned {args.expected_version}")
    if not kernel_build.is_dir() or not (kernel_build / "Makefile").is_file():
        raise SystemExit(f"exact target-kernel build tree is missing: {kernel_build}")
    if output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {output_dir}")
    if shutil.which("make") is None or shutil.which("modinfo") is None:
        raise SystemExit("make and modinfo are required")

    source_git = git_metadata(repo_root)

    build_command = [
        "make", "modules", f"-j{args.jobs}",
        f"SYSSRC={kernel_build}", f"SYSOUT={kernel_build}",
    ]
    plan = {
        "repo_root": str(repo_root),
        "kernel_release": args.kernel_release,
        "kernel_build": str(kernel_build),
        "output_dir": str(output_dir),
        "source_version": source_version,
        "build_command": build_command,
        "signing_requested": args.sign_key is not None,
        "module_paths": list(MODULE_PATHS),
        "claim_boundary": "Build and provenance evidence only; no module is installed or loaded.",
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    output_dir.mkdir(parents=True, exist_ok=False)
    modules_dir = output_dir / "modules"
    modules_dir.mkdir()
    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"
    (output_dir / "commands.txt").write_text(shlex.join(build_command) + "\n")

    build = run(build_command, cwd=repo_root, stdout_path=stdout_path, stderr_path=stderr_path)
    if build.returncode != 0:
        (output_dir / "verdict.md").write_text(
            "# Build verdict\n\nStatus: `FAILED`\n\nNo module was installed or loaded. See `stdout.txt` and `stderr.txt`.\n"
        )
        write_hashes(output_dir)
        raise SystemExit(f"module build failed with exit code {build.returncode}; evidence retained at {output_dir}")

    staged: list[Path] = []
    for relative in MODULE_PATHS:
        source = repo_root / relative
        if not source.is_file():
            raise SystemExit(f"expected module was not produced: {source}")
        destination = modules_dir / source.name
        shutil.copy2(source, destination)
        staged.append(destination)

    if args.sign_key is not None and args.sign_cert is not None:
        if not args.sign_key.is_file() or not args.sign_cert.is_file():
            raise SystemExit("signing key or certificate does not exist")
        for module in staged:
            sign_module(module, kernel_build, args.sign_key.resolve(), args.sign_cert.resolve(), repo_root)

    metadata = [module_metadata(module, args.kernel_release, args.expected_version, repo_root) for module in staged]
    manifest = {
        "schema_version": 1,
        "experiment": "EXP-0006-read-only-nvkms-hdcp",
        "generated_at": utc_now(),
        "source": source_git,
        "source_version": source_version,
        "kernel_release": args.kernel_release,
        "kernel_build": str(kernel_build.resolve()),
        "build_command": build_command,
        "modules": metadata,
        "signing": {
            "requested": args.sign_key is not None,
            "certificate_sha256": sha256_file(args.sign_cert) if args.sign_cert else None,
            "private_key_recorded": False,
        },
        "safety": {
            "installed": False,
            "loaded": False,
            "boot_configuration_changed": False,
            "rebooted": False,
        },
        "claim_boundary": "PROVEN_BUILD only; runtime CAPABILITY_ADVERTISED is not established.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (output_dir / "verdict.md").write_text(
        "# Build verdict\n\nStatus: `PASSED`\n\nHighest state proven: `PROVEN_BUILD` / `SOURCE_PRESENT`.\n\nNo module was installed or loaded. Runtime EXP-0006 remains blocked on recovery review and explicit approval.\n"
    )
    (output_dir / "README.txt").write_text(
        "Exact-kernel EXP-0006 build package. Keep the directory intact and verify artifacts.sha256 before any approved runtime session. The package contains no private signing key.\n"
    )
    write_hashes(output_dir)
    print(f"EXP-0006 exact-kernel build staged at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
