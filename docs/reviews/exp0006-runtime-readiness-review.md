# EXP-0006 runtime-readiness tooling review

Review date: 2026-08-17

## Scope

This change prepares the native RTX 2060 test but does not perform it. It adds:

- a read-only host/source/version/topology preflight;
- an exact-running-kernel module build and provenance packager;
- a renderer for a machine-specific, non-executing rollback plan;
- an operation-scoped approval template;
- a two-clean-boot negative-control/enabled runtime protocol;
- deterministic self-tests and an AST check that confines subprocess execution to an explicit read-only command allowlist.

## Fail-closed properties

- Preflight blocks WSL/non-native execution, a dirty or unidentified source tree, missing exact-kernel headers, missing evidence tools, mismatched NVIDIA modules/userspace, wrong target GPU, wrong module `vermagic`, Nouveau, missing required loaded modules, absent SSH, or incorrect display topology.
- Secure Boot being enabled is reported as a warning rather than a build blocker, but runtime remains blocked until a tested signing/enrollment and recovery path is recorded.
- The build refuses a source-version mismatch, missing merged source symbols, a dirty or unidentified source tree, missing exact-kernel build tree, existing output directory, missing regenerated output module, wrong module version, or wrong `vermagic`.
- Existing expected `.ko` outputs are removed before the exact-kernel build so stale binaries cannot satisfy post-build checks.
- Build artifacts record hashes, a clean source commit, target kernel, module metadata, signature identity, and explicit `installed=false`, `loaded=false`, `rebooted=false` fields.
- The rollback renderer never executes commands. It requires complete known-good identity records for required modules and every optional module that was loaded, then emits loaded-state, path, hash, version, `vermagic`, and parameter verification.
- The approval template separates module operations from reboot approval and explicitly excludes later HDCP, KMS, DRM, playback, and publication work.

## Privacy boundary

The tooling does not intentionally query EDID bytes, host names, account identifiers, hardware serial numbers, credentials, keys, private signing keys, production certificates, license/challenge bodies, CDM data, media samples, or decrypted content. It records local module paths and command/build output because those are required for provenance and recovery; filesystem paths or incidental diagnostic text can contain identifying context. Every artifact must therefore be reviewed before external sharing. Optional signing records only a public-certificate hash and never copies the private key.

## Remaining uncertainty

The tools are self-tested and CI-checkable but cannot prove that a particular native machine is recoverable. Only the operator can verify the known-good boot entry, second-device SSH, local TTY, display mode, physical topology, signing/enrollment state, GSP package identity, and offline recovery materials.

No runtime security-state claim is advanced by this change.
