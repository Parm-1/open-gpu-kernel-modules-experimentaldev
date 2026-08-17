# Authoritative project state

Last updated: 2026-08-17

## Baseline

- Repository: `Parm-1/open-gpu-kernel-modules-experimentaldev`
- NVIDIA source release: `610.57.04`
- Baseline commit: `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Target GPU: GeForce RTX 2060 (Turing)
- Initial route: direct DisplayPort SST, one display, SDR 1920×1080 60 Hz

## Current gate

**Gate 0 hardware baseline: BLOCKED ON NATIVE TARGET EXECUTION**

**Gate 1 read-only query implementation: SOURCE-COMPLETE / BUILD-PASSED / RUNTIME-NOT-RUN**

Highest security state proven remains `SOURCE_PRESENT`. A generic-header module build does not prove `CAPABILITY_ADVERTISED` on the RTX 2060.

## Compiled implementation

- `cd5f5634d552963e1a713306942c57f505b28740` — DisplayPort/RM-owned read-only raw state query.
- `6918273d53ecf844b7495b94dec902049a61bb59` — dedicated NVKMS ioctl and KAPI path.
- `eb6cb2f4dc052709a3bc2445e962c8c9c97d1d51` — default-off `nvidia-drm` structured diagnostic.
- `3759ee6d4fd9c0d13a69d18e988d8409f303e1d0` — append-only ABI ordering correction.

Each source layer passed a complete module build. No module was installed or loaded.

## Next evidence-producing action

After the recovery checklist and explicit module-load approval, execute `docs/runtime/EXP-0006-native-protocol.md` on native Linux and choose one Gate 1 verdict. Authentication control, KMS properties, HDMI, MST, protected decode, and Netflix remain blocked.
