# EXP-0006 runtime-readiness tooling review

Review date: 2026-08-17

## Scope

This change prepares the native RTX 2060 test but does not perform it. It adds:

- a read-only host/source/version/topology preflight;
- an exact-running-kernel module build and provenance packager;
- a renderer for a machine-specific, non-executing rollback plan;
- an operation-scoped approval template;
- a two-clean-boot negative-control/enabled runtime protocol;
- deterministic self-tests and a static check that the preflight contains no privileged module commands.

## Fail-closed properties

- Preflight returns a blocking status for WSL/non-native execution, missing exact-kernel headers, missing evidence tools, mismatched NVIDIA modules/userspace, Nouveau, missing required loaded modules, enabled Secure Boot without a resolved signing path, absent SSH, or incorrect display topology.
- The build refuses a source-version mismatch, missing exact-kernel build tree, existing output directory, missing output module, wrong module version, or wrong `vermagic`.
- Build artifacts record hashes, source commit/dirty state, target kernel, module metadata, signature identity, and explicit `installed=false`, `loaded=false`, `rebooted=false` fields.
- The rollback renderer never executes commands. It requires complete known-good identity records and emits path/version/hash verification steps.
- The approval template separates module operations from reboot approval and explicitly excludes later HDCP, KMS, DRM, playback, and publication work.

## Privacy boundary

The tooling does not collect EDID bytes, host names, account data, serial numbers, credentials, keys, private signing keys, certificates beyond an optional public-certificate hash, license/challenge bodies, CDM data, media samples, or decrypted content.

## Remaining uncertainty

The tools are self-tested and CI-checkable but cannot prove that a particular native machine is recoverable. Only the operator can verify the known-good boot entry, second-device SSH, local TTY, display mode, physical topology, signing/enrollment state, and offline recovery materials.

No runtime security-state claim is advanced by this change.
