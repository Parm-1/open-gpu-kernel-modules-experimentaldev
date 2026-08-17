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

1. the read-only host preflight has no `BLOCK` result;
2. the machine-specific rollback plan is stored offline;
3. modules are built and hashed against the exact running kernel;
4. the human recovery checklist is complete;
5. operation-scoped module-load approval is recorded.

## Runtime protocol

See `docs/runtime/EXP-0006-native-protocol.md`. The protocol uses separate clean-boot default-off and enabled sessions. A successful build or preflight does not establish `CAPABILITY_ADVERTISED`.
