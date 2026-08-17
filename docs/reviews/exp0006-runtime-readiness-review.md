# EXP-0006 runtime-readiness tooling review

Review date: 2026-08-17

## Scope

This change prepares the native RTX 2060 test but does not perform it. It adds:

- a read-only host/source/version/topology preflight;
- an exact-running-kernel module build and provenance packager;
- a renderer for a machine-specific, non-executing rollback plan;
- a read-only post-load verifier that binds approved artifacts to loaded module identity;
- an operation-scoped approval template;
- a three-clean-boot protocol: one default-off negative control and two identical enabled replications;
- a minimized native baseline collector;
- deterministic self-tests and an AST check that confines preflight subprocess execution to an explicit read-only command allowlist.

## Fail-closed properties

- Preflight blocks WSL/non-native execution, a dirty or unidentified source tree, missing exact-kernel headers, missing evidence tools, mismatched NVIDIA modules/userspace, wrong target GPU, wrong module `vermagic`, Nouveau, missing required loaded modules, absent SSH, or incorrect display topology.
- Loaded/on-disk `srcversion` mismatches block preflight; unavailable comparisons remain explicit warnings requiring human resolution.
- Secure Boot being enabled is reported as a warning rather than a build blocker, but runtime remains blocked until a tested signing/enrollment and recovery path is recorded.
- The build refuses a source-version mismatch, missing merged source symbols, a dirty or unidentified source tree, missing exact-kernel build tree, existing output directory, incomplete clean, missing regenerated output module, wrong module version, or wrong `vermagic`.
- The build runs exact-header `make clean` before and after compilation, verifies the repository is clean again, checks that expected `.ko` outputs are absent after cleanup, and replaces build user/host strings with fixed values.
- Build artifacts record hashes, a clean source commit, target kernel, module metadata, signature identity, clean/build return codes, and explicit `installed=false`, `loaded=false`, `rebooted=false` fields.
- The rollback renderer never executes commands. It requires complete known-good identity records for required modules and every optional module that was loaded, then emits loaded-state, path, hash, version, `vermagic`, available `srcversion`, and parameter verification.
- The loaded-build verifier fails unless the approved manifest hash, staged module hashes, target kernel, clean build record, loaded versions/`srcversion`, and `nvidia_drm` parameters all match.
- The runtime protocol requires successful `modetest`, one direct NVIDIA DP-SST connector, an artifact-bound negative control, two separately booted enabled observations, and verified known-good restoration after every session.
- The approval template separates each session's stop/unload/load/control/restore/reboot operations and explicitly excludes later HDCP, KMS, DRM, playback, service, and publication work.

## Privacy boundary

The tooling does not intentionally query EDID bytes, host names, account identifiers, hardware serial numbers, credentials, keys, private signing keys, production certificates, license/challenge bodies, CDM data, media samples, or decrypted content. The baseline collector excludes the hostname from `uname`, removes broad `drm_info` and bug-report collection, stores only EDID presence/size, and limits `nvidia-smi` fields. Local module paths, PCI topology, kernel parameters, and command/build logs remain necessary for provenance and recovery and can contain identifying context. Every artifact must therefore be reviewed before external sharing. Optional signing records only a public-certificate hash and never copies the private key.

## Remaining uncertainty

The tools are self-tested and CI-checkable but cannot prove that a particular native machine is recoverable. Only the operator can verify the known-good boot entry, second-device SSH, local TTY, display mode, physical topology, signing/enrollment state, GSP package identity, and offline recovery materials. The post-load verifier establishes software identity, not that RM/GSP will authorize or meaningfully answer the HDCP query.

No runtime security-state claim is advanced by this change.
