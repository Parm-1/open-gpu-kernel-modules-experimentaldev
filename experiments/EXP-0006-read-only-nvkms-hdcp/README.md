# EXP-0006: Query authoritative HDCP state through NVKMS

## Question

Can a community-built, read-only bridge retrieve meaningful DP HDCP state from the normal GeForce RTX 2060 Linux RM/GSP path?

## Implementation status

The implementation is merged in `e9507b77cd2075c82ad34353660666ae58ccf502`. Its final PR head passed all six checks, including complete module compilation. Runtime has not been run; no experimental module has been installed or loaded.

The default-off `hdcp_probe=1` diagnostic preserves:

- NVKMS transport success/failure;
- detailed DP bridge result;
- exact RM status;
- consolidated raw state flags;
- validity.

It performs no authentication, stream-type, ECF, KMS-property, modeset, protected-playback, or service operation.

## Current blocker

Runtime remains blocked until:

1. the read-only host preflight has no `BLOCK` result and every warning is resolved;
2. loaded/on-disk known-good module identity is verified and the rollback plan is stored offline;
3. modules are clean-built, validated, and hashed against the exact running kernel;
4. the human recovery checklist is complete;
5. operation- and session-scoped module/reboot approval is recorded.

## Runtime protocol

See `docs/runtime/EXP-0006-native-protocol.md`. The protocol binds every session to one approved build manifest and requires three clean boots:

1. default-off negative control;
2. enabled read-only run 1;
3. enabled read-only run 2 under identical controls.

Each session requires successful loaded-module identity verification, successful `modetest`, one direct NVIDIA DP-SST connector, complete logs/hashes, and verified known-good restoration. A successful preflight, build, load, or identity check does not establish `CAPABILITY_ADVERTISED`; only the reviewed RM/GSP query result can advance Gate 1.
