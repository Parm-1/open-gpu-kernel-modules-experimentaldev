# EXP-0006: Query authoritative HDCP state through NVKMS

## Question

Can a community-built, read-only bridge retrieve meaningful DP HDCP state from the normal GeForce RTX 2060 Linux RM/GSP path?

## Implementation status

Source-complete and repeatedly full-module-build-passed. Runtime not run. No module has been installed or loaded.

The default-off `hdcp_probe=1` diagnostic preserves:

- NVKMS transport success/failure;
- detailed DP bridge result;
- exact RM status;
- consolidated raw state flags;
- validity.

It performs no authentication or stream-type operation.

## Runtime protocol

See `docs/runtime/EXP-0006-native-protocol.md`. Loading/rebooting remains blocked until the recovery checklist is complete and explicit approval is recorded.
