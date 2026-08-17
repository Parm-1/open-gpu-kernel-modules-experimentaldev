# Native test recovery checklist

Complete every item before requesting approval to load an experimental module.

- [ ] Native Linux test installation is expendable or separately recoverable.
- [ ] A known-good kernel and NVIDIA driver boot entry is present and tested.
- [ ] SSH from a second device works before the graphics experiment.
- [ ] Local TTY login works.
- [ ] Exact rollback commands are saved offline.
- [ ] Kernel modules, userspace driver, and GSP firmware use the same NVIDIA release.
- [ ] Secure Boot state and module-signing procedure are understood.
- [ ] Windows partitions are not modified by the experiment.
- [ ] Only one direct DisplayPort display is active.
- [ ] HDR, VRR, MST, adapters, docks, KVMs, receivers, and secondary outputs are disabled or removed.
- [ ] A remote command can restore the known-good module and reboot safely.
- [ ] Baseline bug report, `drm_info`, `modetest`, and module hashes are archived.
- [ ] Explicit approval to install/load/reboot has been recorded.
