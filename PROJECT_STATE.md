# Authoritative project state

Last updated: 2026-08-17

## Baseline

- Repository: `Parm-1/open-gpu-kernel-modules-experimentaldev`
- NVIDIA source release: `610.57.04`
- Upstream source baseline: `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Read-only implementation merge: `e9507b77cd2075c82ad34353660666ae58ccf502`
- Final implementation head: `de4bc76f4c9f1575b3527f95da719c5e1cb7e708`
- Runtime-readiness implementation head: `94a50cc2b6199b9804c30bbf2a101278742e5134`
- Target GPU: GeForce RTX 2060 (Turing)
- Initial route: direct DisplayPort SST, one display, SDR 1920×1080 60 Hz

## Current gate

**Gate 0 hardware baseline: BLOCKED ON NATIVE TARGET EXECUTION**

**Gate 1 read-only query implementation: MERGED / FULL-MODULE-BUILD-PASSED / RUNTIME-NOT-RUN**

**Gate 1 runtime readiness: TOOLING-COMPLETE / CI-PASSED / NATIVE-PREFLIGHT-NOT-RUN**

Highest security state proven remains `SOURCE_PRESENT`. Generic-header compilation, runtime-tool self-tests, module-identity validation, and protocol preparation do not prove `CAPABILITY_ADVERTISED` on the RTX 2060.

## Compiled implementation

- `cd5f5634d552963e1a713306942c57f505b28740` — DisplayPort/RM-owned read-only raw state query.
- `6918273d53ecf844b7495b94dec902049a61bb59` — dedicated NVKMS ioctl and KAPI path.
- `eb6cb2f4dc052709a3bc2445e962c8c9c97d1d51` — default-off `nvidia-drm` structured diagnostic.
- `3759ee6d4fd9c0d13a69d18e988d8409f303e1d0` — append-only ABI ordering correction.
- `de4bc76f4c9f1575b3527f95da719c5e1cb7e708` — final implementation head; all six checks passed, including complete module compilation.
- `e9507b77cd2075c82ad34353660666ae58ccf502` — implementation merge to `main`; all post-merge research and decoder checks passed.

No experimental module has been installed or loaded, no boot configuration has changed, and no reboot has been performed.

## Runtime-readiness tooling

The repository now contains:

- a read-only, command-confined native preflight;
- loaded-versus-on-disk NVIDIA module identity checks;
- an exact-running-kernel clean-build and provenance packager;
- deterministic build user/host values;
- a machine-specific, non-executing rollback-plan renderer;
- a read-only verifier that binds an approved build manifest to the loaded modules and `nvidia_drm` parameters;
- a minimized native baseline collector that excludes EDID contents, broad DRM dumps, hardware UUID queries, and vendor bug reports;
- an operation- and session-scoped approval record;
- one default-off negative-control session and two separately booted enabled replications;
- CI syntax, confinement, privacy, smoke, complete-module-build, module-identity, and post-build-cleanup checks.

Candidate head `94a50cc2b6199b9804c30bbf2a101278742e5134` passed all seven PR checks, including the complete NVIDIA module build. These results prove tooling/build integrity only.

## Next evidence-producing action

On the native RTX 2060 machine:

1. run the read-only EXP-0006 preflight from a clean checkout;
2. resolve every blocker and warning, verify SSH/TTY and the known-good boot entry, and store the rollback material offline;
3. create and hash an exact-running-kernel clean-build package;
4. complete the recovery checklist and record operation-scoped approval bound to that exact package;
5. run the default-off negative control from a clean boot and verify known-good restoration;
6. run enabled read-only observation 1 from a clean boot and restore;
7. run enabled read-only observation 2 under identical controls from another clean boot and restore;
8. review all three sessions and assign one Gate 1 verdict.

Authentication control, Type 0/Type 1 selection, KMS content-protection properties, HDMI, MST, protected decode, and service testing remain blocked.
