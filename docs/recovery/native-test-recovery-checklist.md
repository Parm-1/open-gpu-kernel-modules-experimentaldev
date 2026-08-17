# Native test recovery checklist

Complete every item before requesting approval to load an experimental module. Script output can support this review but cannot complete human-only items.

## Automated evidence

- [ ] `scripts/exp0006-preflight.py` completed on native Linux with no `BLOCK` result.
- [ ] The preflight directory passes `sha256sum -c artifacts.sha256`.
- [ ] `known-good-modules.json` and the rendered machine-specific rollback plan are stored on a second device.
- [ ] `scripts/build-exp0006.py` completed against the exact running kernel.
- [ ] The build directory passes `sha256sum -c artifacts.sha256`.
- [ ] Every staged module reports NVIDIA version `610.57.04` and target-kernel `vermagic`.
- [ ] Module signature state is compatible with the recorded Secure Boot policy.

## Human recovery checks

- [ ] Native Linux test installation is expendable or separately recoverable.
- [ ] A known-good kernel and NVIDIA driver boot entry is present and has been boot-tested.
- [ ] SSH from a second device works in the current boot.
- [ ] Local TTY login works in the current boot.
- [ ] Exact rollback commands, module paths, hashes, versions, and boot-entry instructions are saved offline.
- [ ] Kernel modules, userspace driver, and GSP firmware use the same NVIDIA `610.57.04` release.
- [ ] Secure Boot state and module-signing/enrollment procedure are understood and tested.
- [ ] Windows partitions are not modified by the experiment.
- [ ] Only one direct DisplayPort SST display is active.
- [ ] The display is SDR 1920×1080 60 Hz.
- [ ] HDR, VRR, MST, adapters, docks, KVMs, receivers, capture devices, and secondary outputs are disabled or removed.
- [ ] The known-good stack can be restored from SSH without force-removing a module.
- [ ] Baseline bug report, `drm_info`, `modetest`, module metadata, and hashes are archived.

## Approval scope

- [ ] `docs/runtime/EXP-0006-approval-template.md` has been filled in for this exact host state and build.
- [ ] Explicit approval to stop the graphical target and unload/load modules has been recorded.
- [ ] Approval for the default-off control and enabled probe sessions has been recorded separately.
- [ ] Reboot approval has been recorded separately if a reboot may be used.

If any item is false or ambiguous, the runtime experiment remains blocked.
