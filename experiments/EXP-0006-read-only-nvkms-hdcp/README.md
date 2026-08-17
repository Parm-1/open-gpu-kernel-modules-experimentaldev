# EXP-0006: Query authoritative HDCP state through NVKMS

## Question

Can a community-built read-only bridge retrieve meaningful DP HDCP state from the shipping RM/GSP path?

## Acceptance criterion

A truthful query preserves raw errors and yields one Gate 1 verdict; it performs no control operation.

## Safety

Requires a custom module, recovery checkpoint, and explicit load/reboot approval. The patch itself remains read-only.
