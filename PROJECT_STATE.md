# Authoritative project state

Last updated: 2026-08-17

## Baseline

- Repository: `Parm-1/open-gpu-kernel-modules-experimentaldev`
- NVIDIA source release: `610.57.04`
- Baseline commit: `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Target GPU: GeForce RTX 2060 (Turing)
- Initial physical route: direct DisplayPort, one display, SDR 1920×1080 at 60 Hz, no adapters, docks, MST, secondary outputs, HDR, or VRR

## Current gate

**Gate 0 — reproducible baseline: IN PROGRESS**

The source half of Gate 0 is implemented by the foundation branch. Native Linux connector ownership, KMS properties, Vulkan runtime capabilities, monitor EDID hash, and the same-hardware Windows reference require execution on the target machine.

## Proven from pinned public source

1. `590.48.01` hard-codes DisplayPort HDCP state as unsupported.
2. `595.44.02` contains RM-backed HDCP query and control paths.
3. `610.57.04` retains HDCP 1.x/2.2 state parsing, authentication control, link validation, Type 0/Type 1 selection, and DP group encryption management.
4. Current `nvidia-drm` does not attach the standard Linux content-protection properties.
5. Current public NVKMS KAPI exposes no dedicated HDCP query, request, status, or event surface.

These are `SOURCE_PRESENT` findings only.

## Highest-information next experiment

Implement a DisplayPort-SST-only, read-only NVKMS HDCP state query that reaches the authoritative DP/RM-owned state, returns capability/authentication/encryption/Type 1/raw status fields, performs no control operation, and preserves failure as data.

See `docs/implementation/read-only-nvkms-query-design.md` and `experiments/EXP-0006-read-only-nvkms-hdcp/`.

## Explicit blockers

- No native target-machine measurements have been collected.
- No modified module has been built against the target kernel or loaded.
- The source path from an NVKMS display object to the DP library's HDCP state owner is not yet implemented or proven.
- Vendor attestation and Netflix authorization remain unproven.
