#!/usr/bin/env python3
"""Build and stage EXP-0006 modules for the exact running kernel.

The tool is build-only. It never installs, unloads, loads, changes boot state,
or reboots. It performs exact-header pre/post cleaning, verifies the source tree
is clean again, and replaces build user/host strings with fixed values. Optional
signing happens only when both explicit local inputs are provided; the private
key is never copied into the evidence directory.
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
FIXED_BUILD_USER = "exp0006"
FIXED_BUILD_HOST = "exp0006"
REQUIRED_SOURCE_SYMBOLS = {
    "src/common/displayport/src/dp_evoadapter.cpp": "queryHDCPRawState",
    "src/nvidia-modeset/src/nvkms.c": "NVKMS_IOCTL_QUERY_DPY_HDCP_STATE",
    "kernel-open/common/inc/nvkms-kapi.h": "queryHdcpState",
    "kernel-open/nvidia-drm/nvidia-drm-connector.c": "HDCP_PROBE",
}
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


def run(
    argv: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "LC_ALL": "C",
        "NV_BUILD_USER": FIXED_BUILD_USER,
        "NV_BUILD_HOST": FIXED_BUILD_HOST,
        "KBUILD_BUILD_USER": FIXED_BUILD_USER,
        "KBUILD_BUILD_HOST": FIXED_BUILD_HOST,
    }
    if stdout_path is None or stderr_path is None:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    with stdout_path.open("w") as stdout_stream, stderr_path.open("w") as stderr_stream:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            check=False,
            stdout=stdout_stream,
            stderr=stderr_stream,
            text=True,
            env=env,
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
    if head.returncode != 0 or not head.stdout.strip():
        raise RuntimeError("source tree is not a readable Git checkout")
    if status.returncode != 0:
        raise RuntimeError("source cleanliness could not be determined")
    if status.stdout.strip():
        raise RuntimeError("source tree has uncommitted or untracked changes")
    return {"commit": head.stdout.strip(), "dirty": False}


def verify_clean_after_build(repo_root: Path) -> dict[str, Any]:
    status = run(["git", "status", "--porcelain"], cwd=repo_root)
    if status.returncode != 0:
        raise RuntimeError("post-build source cleanliness could not be determined")
    dirty_entries = [line for line in status.stdout.splitlines() if line.strip()]
    leftovers = [relative for relative in MODULE_PATHS if (repo_root / relative).exists()]
    if dirty_entries or leftovers:
        raise RuntimeError(
            "post-build cleanup left source-tree artifacts: "
            + ", ".join(dirty_entries + leftovers)
        )
    return {"dirty": False, "leftover_expected_modules": []}


def verify_source(repo_root: Path) -> None:
    missing: list[str] = []
    for relative, symbol in REQUIRED_SOURCE_SYMBOLS.items():
        path = repo_root / relative
        try:
            text = path.read_text(errors="strict")
        except OSError:
            text = ""
        if symbol not in text:
            missing.append(f"{relative}:{symbol}")
    if missing:
        raise RuntimeError("required merged source symbols are missing: " + ", ".join(missing))


def make_commands(kernel_build: Path, jobs: int) -> tuple[list[str], list[str]]:
    common = [
        f"SYSSRC={kernel_build}",
        f"SYSOUT={kernel_build}",
        f"NV_BUILD_USER={FIXED_BUILD_USER}",
        f"NV_BUILD_HOST={FIXED_BUILD_HOST}",
        f"KBUILD_BUILD_USER={FIXED_BUILD_USER}",
        f"KBUILD_BUILD_HOST={FIXED_BUILD_HOST}",
    ]
    clean_command = ["make", "clean", *common]
    build_command = ["make", f"-j{jobs}", "modules", *common]
    return clean_command, build_command


def expected_module_outputs(repo_root: Path) -> list[str]:
    return [relative for relative in MODULE_PATHS if (repo_root / relative).exists()]


def sign_module(
    module: Path,
    kernel_build: Path,
    key: Path,
    certificate: Path,
    repo_root: Path,
) -> None:
    sign_file = kernel_build / "scripts" / "sign-file"
    if not sign_file.is_file():
        raise RuntimeError(f"kernel sign-file helper not found: {sign_file}")
    result = run(
        [str(sign_file), "sha256", str(key), str(certificate), str(module)],
        cwd=repo_root,
    )
    if result.returncode != 0:
        raise RuntimeError(f"module signing failed for {module.name}: {result.stderr.strip()}")


def module_metadata(
    module: Path,
    kernel_release: str,
    expected_version: str,
    repo_root: Path,
) -> dict[str, Any]:
    version = command_output(["modinfo", "-F", "version", str(module)], cwd=repo_root)
    vermagic = command_output(["modinfo", "-F", "vermagic", str(module)], cwd=repo_root)
    signer = command_output(["modinfo", "-F", "signer", str(module)], cwd=repo_root)
    srcversion = command_output(["modinfo", "-F", "srcversion", str(module)], cwd=repo_root)
    if version != expected_version:
        raise RuntimeError(f"{module.name}: version {version!r} does not match {expected_version!r}")
    if not vermagic_matches(vermagic, kernel_release):
        raise RuntimeError(
            f"{module.name}: vermagic {vermagic!r} does not match kernel {kernel_release!r}"
        )
    return {
        "name": module.name,
        "relative_path": f"modules/{module.name}",
        "size": module.stat().st_size,
        "sha256": sha256_file(module),
        "version": version,
        "vermagic": vermagic,
        "signer": signer or None,
        "srcversion": srcversion or None,
    }


def write_hashes(output_dir: Path) -> None:
    lines = [
        f"{sha256_file(path)}  {path.relative_to(output_dir)}"
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name != "artifacts.sha256"
    ]
    (output_dir / "artifacts.sha256").write_text("\n".join(lines) + "\n")


def write_failure(output_dir: Path, message: str) -> None:
    (output_dir / "verdict.md").write_text(
        "# Build verdict\n\n"
        "Status: `FAILED`\n\n"
        f"Reason: {message}\n\n"
        "No module was installed or loaded.\n"
    )
    (output_dir / "README.txt").write_text(
        "Failed exact-kernel EXP-0006 build package. Review local filesystem paths in logs before sharing. No module was installed or loaded.\n"
    )
    write_hashes(output_dir)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        version_mk = root / "version.mk"
        version_mk.write_text(
            "NVIDIA_VERSION = 610.57.04\nNVIDIA_NVID_VERSION = 610.57.04\n"
        )
        assert parse_version_mk(version_mk) == EXPECTED_VERSION
        sample = root / "sample"
        sample.write_bytes(b"abc")
        assert sha256_file(sample) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        clean_command, build_command = make_commands(root, 2)
        assert clean_command[:2] == ["make", "clean"]
        assert build_command[:3] == ["make", "-j2", "modules"]
        assert "NV_BUILD_USER=exp0006" in build_command
        assert "KBUILD_BUILD_HOST=exp0006" in build_command
    assert vermagic_matches(
        "6.8.0-137-generic SMP preempt mod_unload", "6.8.0-137-generic"
    )
    assert not vermagic_matches("6.8.0-136-generic SMP", "6.8.0-137-generic")
    print("build-exp0006 self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--kernel-release", default=platform.release())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--jobs", type=int, default=max(1, min(4, os.cpu_count() or 1))
    )
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
    output_dir = args.output_dir or (
        repo_root
        / "artifacts"
        / f"EXP-0006-build-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    try:
        source_version = parse_version_mk(repo_root / "version.mk")
        if source_version != args.expected_version:
            raise RuntimeError(
                f"source version {source_version} does not match pinned {args.expected_version}"
            )
        verify_source(repo_root)
        source_git = git_metadata(repo_root)
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc

    if not kernel_build.is_dir() or not (kernel_build / "Makefile").is_file():
        raise SystemExit(f"exact target-kernel build tree is missing: {kernel_build}")
    if output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {output_dir}")
    if shutil.which("make") is None or shutil.which("modinfo") is None:
        raise SystemExit("make and modinfo are required")
    if args.sign_key and (
        not args.sign_key.is_file()
        or args.sign_cert is None
        or not args.sign_cert.is_file()
    ):
        raise SystemExit("signing key or certificate does not exist")

    clean_command, build_command = make_commands(kernel_build, args.jobs)
    plan = {
        "kernel_release": args.kernel_release,
        "kernel_build": str(kernel_build),
        "source_commit": source_git["commit"],
        "source_version": source_version,
        "clean_command": clean_command,
        "build_command": build_command,
        "fixed_build_identity": {
            "NV_BUILD_USER": FIXED_BUILD_USER,
            "NV_BUILD_HOST": FIXED_BUILD_HOST,
            "KBUILD_BUILD_USER": FIXED_BUILD_USER,
            "KBUILD_BUILD_HOST": FIXED_BUILD_HOST,
        },
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
    (output_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    (output_dir / "commands.txt").write_text(
        shlex.join(clean_command) + "\n"
        + shlex.join(build_command) + "\n"
        + shlex.join(clean_command) + "\n"
    )

    preclean = run(
        clean_command,
        cwd=repo_root,
        stdout_path=output_dir / "preclean.stdout.txt",
        stderr_path=output_dir / "preclean.stderr.txt",
    )
    if preclean.returncode != 0:
        write_failure(output_dir, f"pre-build make clean exited {preclean.returncode}")
        raise SystemExit(f"pre-build cleanup failed; evidence retained at {output_dir}")
    preclean_leftovers = expected_module_outputs(repo_root)
    if preclean_leftovers:
        write_failure(
            output_dir,
            "pre-build cleanup left expected modules: " + ", ".join(preclean_leftovers),
        )
        raise SystemExit(f"pre-build cleanup was incomplete; evidence retained at {output_dir}")

    build = run(
        build_command,
        cwd=repo_root,
        stdout_path=output_dir / "build.stdout.txt",
        stderr_path=output_dir / "build.stderr.txt",
    )

    failure: str | None = None
    metadata: list[dict[str, Any]] = []
    try:
        if build.returncode != 0:
            raise RuntimeError(f"make modules exited {build.returncode}")

        staged: list[Path] = []
        for relative in MODULE_PATHS:
            source = repo_root / relative
            if not source.is_file():
                raise RuntimeError(f"expected module was not produced: {relative}")
            destination = modules_dir / source.name
            shutil.copy2(source, destination)
            staged.append(destination)

        if args.sign_key is not None and args.sign_cert is not None:
            for module in staged:
                sign_module(
                    module,
                    kernel_build,
                    args.sign_key.resolve(),
                    args.sign_cert.resolve(),
                    repo_root,
                )

        metadata = [
            module_metadata(
                module, args.kernel_release, args.expected_version, repo_root
            )
            for module in staged
        ]
    except (OSError, RuntimeError) as exc:
        failure = str(exc)

    postclean = run(
        clean_command,
        cwd=repo_root,
        stdout_path=output_dir / "postclean.stdout.txt",
        stderr_path=output_dir / "postclean.stderr.txt",
    )
    cleanup_record: dict[str, Any] = {
        "preclean_returncode": preclean.returncode,
        "build_returncode": build.returncode,
        "postclean_returncode": postclean.returncode,
    }
    if postclean.returncode != 0:
        cleanup_record["clean_tree_verified"] = False
        failure = failure or f"post-build make clean exited {postclean.returncode}"
    else:
        try:
            cleanup_record.update(verify_clean_after_build(repo_root))
            cleanup_record["clean_tree_verified"] = True
        except RuntimeError as exc:
            cleanup_record["clean_tree_verified"] = False
            cleanup_record["verification_error"] = str(exc)
            failure = failure or str(exc)
    (output_dir / "cleanup.json").write_text(
        json.dumps(cleanup_record, indent=2, sort_keys=True) + "\n"
    )

    if failure is not None:
        write_failure(output_dir, failure)
        raise SystemExit(
            f"exact-kernel build validation failed; evidence retained at {output_dir}: {failure}"
        )

    manifest = {
        "schema_version": 1,
        "experiment": "EXP-0006-read-only-nvkms-hdcp",
        "generated_at": utc_now(),
        "source": source_git,
        "source_version": source_version,
        "kernel_release": args.kernel_release,
        "kernel_build": str(kernel_build.resolve()),
        "clean_command": clean_command,
        "build_command": build_command,
        "cleanup": cleanup_record,
        "fixed_build_identity": plan["fixed_build_identity"],
        "modules": metadata,
        "signing": {
            "requested": args.sign_key is not None,
            "certificate_sha256": sha256_file(args.sign_cert)
            if args.sign_cert
            else None,
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
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "verdict.md").write_text(
        "# Build verdict\n\n"
        "Status: `PASSED`\n\n"
        "Highest state proven: `PROVEN_BUILD` / `SOURCE_PRESENT`.\n\n"
        "The source tree was cleaned before and after the exact-kernel build. No module was installed or loaded. Runtime EXP-0006 remains blocked on recovery review and explicit approval.\n"
    )
    (output_dir / "README.txt").write_text(
        "Exact-kernel EXP-0006 build package. Verify artifacts.sha256 and review local filesystem paths in logs before sharing. Fixed build user/host strings were used, and the package contains no private signing key.\n"
    )
    write_hashes(output_dir)
    print(f"EXP-0006 exact-kernel build staged at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
