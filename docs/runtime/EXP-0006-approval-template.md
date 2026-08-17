# EXP-0006 execution approval record

This record is intentionally incomplete until a human fills it in. Committing the template does not grant approval.

## Identity

- Repository commit:
- NVIDIA source version: `610.57.04`
- Target kernel release:
- Operator-defined machine alias (do not use a serial number):
- Approved preflight directory:
- Preflight `artifacts.sha256` SHA-256:
- `known-good-modules.json` SHA-256:
- `rollback-plan.md` SHA-256:
- Approved exact-kernel build directory (absolute local path):
- Exact-kernel `manifest.json` SHA-256:
- Build `artifacts.sha256` SHA-256:
- Experimental module signer identity, or `UNSIGNED_WITH_SECURE_BOOT_DISABLED`:

## Recovery evidence

- [ ] Native test installation is expendable or independently recoverable.
- [ ] Known-good kernel/NVIDIA boot entry has been boot-tested.
- [ ] SSH from a second device has been tested in the current boot.
- [ ] Local TTY login has been tested.
- [ ] Machine-specific rollback plan and its source snapshot are stored offline.
- [ ] Known-good loaded modules match their recorded on-disk paths, hashes, versions, `vermagic`, and available `srcversion`.
- [ ] Build manifest records successful pre-clean, exact-kernel build, post-clean, and clean-tree verification.
- [ ] Installed userspace, known-good modules, experimental modules, and GSP firmware all match `610.57.04`.
- [ ] Secure Boot/signature handling is resolved and tested.
- [ ] One direct NVIDIA DisplayPort SST output is active at SDR 1920×1080 60 Hz.
- [ ] HDR, VRR, MST, adapters, docks, KVMs, receivers, capture devices, and secondary outputs are absent or disabled.
- [ ] Baseline and diagnostic artifacts were reviewed for local paths or other identifying context before any sharing.

## Scope of approval

Mark each operation separately. Unmarked operations remain prohibited.

- [ ] Stop the graphical target for the default-off negative control.
- [ ] Unload the currently loaded NVIDIA modules without force for the negative control.
- [ ] Load the exact locally built modules recorded in the approved manifest for the negative control.
- [ ] Run the default-off negative-control session.
- [ ] Restore and verify the recorded known-good module stack after the negative control.
- [ ] Reboot to the known-good boot entry before enabled run 1.
- [ ] Stop, unload, and load the identical approved build for enabled run 1.
- [ ] Run enabled read-only run 1 with `hdcp_probe=1`.
- [ ] Restore and verify the recorded known-good module stack after enabled run 1.
- [ ] Reboot to the known-good boot entry before enabled run 2.
- [ ] Stop, unload, and load the identical approved build for enabled run 2.
- [ ] Run enabled read-only run 2 with `hdcp_probe=1`.
- [ ] Restore and verify the recorded known-good module stack after enabled run 2.
- [ ] Reboot to the known-good boot entry after enabled run 2.

This approval does **not** authorize HDCP authentication, Type 0/Type 1 selection, ECF changes, standard KMS content-protection properties, DRM/CDM work, protected media playback, service testing, key/certificate/license collection, or publication to an external project/vendor.

## Approval

- Approved by:
- Approval timestamp with time zone:
- Approval statement:
- Additional constraints:

## Negative-control session result

- Session start:
- Session end:
- Artifact directory:
- Approved build manifest reverified immediately before load: `YES` / `NO`
- Loaded-build verifier passed: `YES` / `NO`
- Successful direct-DP `modetest` and topology check: `YES` / `NO`
- No `HDCP_PROBE` record observed: `YES` / `NO`
- Known-good restoration verified: `YES` / `NO`
- Notes:

## Enabled read-only run 1 result

- Session start:
- Session end:
- Artifact directory:
- Approved build manifest reverified immediately before load: `YES` / `NO`
- Loaded-build verifier passed with `hdcp_probe=Y`: `YES` / `NO`
- Successful direct-DP `modetest` and topology check: `YES` / `NO`
- Decoder completed: `YES` / `NO`
- Known-good restoration verified: `YES` / `NO`
- Notes:

## Enabled read-only run 2 result

- Session start:
- Session end:
- Artifact directory:
- Approved build manifest reverified immediately before load: `YES` / `NO`
- Loaded-build verifier passed with `hdcp_probe=Y`: `YES` / `NO`
- Successful direct-DP `modetest` and topology check: `YES` / `NO`
- Decoder completed: `YES` / `NO`
- Result matches run 1 under unchanged controls: `YES` / `NO`
- Known-good restoration verified: `YES` / `NO`
- Preliminary Gate 1 verdict: `NOT_ASSIGNED`
- Notes:
