# EXP-0006 execution approval record

This record is intentionally incomplete until a human fills it in. Committing the template does not grant approval.

## Identity

- Repository commit:
- NVIDIA source version: `610.57.04`
- Target kernel release:
- Preflight `artifacts.sha256` SHA-256:
- `known-good-modules.json` SHA-256:
- Exact-kernel `manifest.json` SHA-256:
- Build `artifacts.sha256` SHA-256:
- Operator-defined machine alias (do not use a serial number):

## Recovery evidence

- [ ] Native test installation is expendable or independently recoverable.
- [ ] Known-good kernel/NVIDIA boot entry has been boot-tested.
- [ ] SSH from a second device has been tested in the current boot.
- [ ] Local TTY login has been tested.
- [ ] Machine-specific rollback plan is stored offline.
- [ ] Installed userspace, known-good modules, experimental modules, and GSP firmware all match `610.57.04`.
- [ ] Secure Boot/signature handling is resolved and tested.
- [ ] One direct NVIDIA DisplayPort SST output is active at SDR 1920×1080 60 Hz.
- [ ] HDR, VRR, MST, adapters, docks, KVMs, receivers, capture devices, and secondary outputs are absent or disabled.

## Scope of approval

Mark each operation separately. Unmarked operations remain prohibited.

- [ ] Stop the graphical target.
- [ ] Unload the currently loaded NVIDIA display modules without force.
- [ ] Load the exact locally built modules recorded in the build manifest.
- [ ] Run the default-off negative-control session.
- [ ] Run the `hdcp_probe=1` read-only session.
- [ ] Restore and verify the recorded known-good module stack.
- [ ] Reboot to the known-good boot entry after a session.

This approval does **not** authorize HDCP authentication, Type 0/Type 1 selection, ECF changes, standard KMS content-protection properties, DRM/CDM work, protected media playback, service testing, key/certificate/license collection, or publication to an external project/vendor.

## Approval

- Approved by:
- Approval timestamp with time zone:
- Approval statement:
- Additional constraints:

## Session result

- Session start:
- Session end:
- Artifact directory:
- Restoration verified:
- Preliminary Gate 1 verdict: `NOT_ASSIGNED`
- Notes:
