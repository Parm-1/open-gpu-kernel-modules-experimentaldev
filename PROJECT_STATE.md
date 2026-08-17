# Authoritative project state

Last updated: 2026-08-17

## Baseline

- Repository: `Parm-1/open-gpu-kernel-modules-experimentaldev`
- NVIDIA source release: `610.57.04`
- Upstream source baseline: `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Read-only implementation merge: `e9507b77cd2075c82ad34353660666ae58ccf502`
- Reviewed implementation head: `de4bc76f4c9f1575b3527f95da719c5e1cb7e708`
- Target GPU: GeForce RTX 2060 (Turing)
- Initial route: direct DisplayPort SST, one display, SDR 1920×1080 60 Hz

## Current gate

**Gate 0 hardware baseline: BLOCKED ON NATIVE TARGET EXECUTION**

**Gate 1 read-only query implementation: MERGED / FULL-MODULE-BUILD-PASSED / RUNTIME-NOT-RUN**

Highest security state proven remains `SOURCE_PRESENT`. A generic-header module build does not prove `CAPABILITY_ADVERTISED` on the RTX 2060.

## Compiled implementation

- `cd5f5634d552963e1a713306942c57f505b28740` — DisplayPort/RM-owned read-only raw state query.
- `6918273d53ecf844b7495b94dec902049a61bb59` — dedicated NVKMS ioctl and KAPI path.
- `eb6cb2f4dc052709a3bc2445e962c8c9c97d1d51` — default-off `nvidia-drm` structured diagnostic.
- `3759ee6d4fd9c0d13a69d18e988d8409f303e1d0` — append-only ABI ordering correction.
- `de4bc76f4c9f1575b3527f95da719c5e1cb7e708` — final reviewed PR head; all six checks passed, including `compile-modules`.
- `e9507b77cd2075c82ad34353660666ae58ccf502` — merge to `main`; all post-merge research/decoder checks passed.

No experimental module has been installed or loaded, no boot configuration has changed, and no reboot has been performed.

## Runtime readiness

The next repository change adds a read-only native preflight, exact-target-kernel build packager, machine-specific rollback-plan renderer, approval template, and CI self-tests. These tools prepare evidence and recovery review only; they do not authorize or perform module operations.

## Next evidence-producing action

On the native RTX 2060 machine:

1. run the read-only EXP-0006 preflight;
2. resolve every blocker and complete the human recovery checklist;
3. build and hash modules against the exact running kernel;
4. obtain explicit operation-scoped approval;
5. execute the two-session default-off/enabled protocol;
6. assign one Gate 1 verdict.

Authentication control, KMS properties, HDMI, MST, protected decode, and service testing remain blocked.
