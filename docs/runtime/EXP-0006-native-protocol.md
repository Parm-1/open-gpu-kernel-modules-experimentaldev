# EXP-0006 native runtime protocol

Status: `BLOCKED_PENDING_RECOVERY_AND_EXPLICIT_LOAD_APPROVAL`

## Objective

Classify whether the RTX 2060's native Linux RM/GSP path permits the compiled read-only HDCP state query. This protocol performs no authentication request, stream-type selection, KMS content-protection property change, or media playback.

## Required topology

```text
RTX 2060 → direct DisplayPort cable → one HDCP 2.2/2.3-capable display
```

Use native Linux, SDR 1920×1080 60 Hz, no secondary output, MST, adapter, dock, KVM, receiver, capture device, HDR, or VRR.

## Checkpoint

Before any module installation/load or reboot:

1. Complete `docs/recovery/native-test-recovery-checklist.md`.
2. Verify SSH and a local TTY from a known-good driver boot.
3. Match the experimental kernel modules, installed NVIDIA userspace, and GSP firmware to 610.57.04.
4. Archive the unmodified baseline from `scripts/collect-native-baseline.sh`.
5. Record the known-good module paths and rollback commands offline.
6. Record explicit approval for the module-load/reboot operation.

## Build-only validation already completed

The branch has repeatedly completed a full module build against generic kernel headers. Before runtime, rebuild against the exact target kernel:

```bash
kernel_release="$(uname -r)"
kernel_build="/lib/modules/$kernel_release/build"
test -d "$kernel_build"
make modules -j2 SYSSRC="$kernel_build" SYSOUT="$kernel_build"
```

That remains source/build evidence only.

## Prove module identity before loading

Run from the repository root and retain these outputs:

```bash
experimental_modules=(
  kernel-open/nvidia.ko
  kernel-open/nvidia-modeset.ko
  kernel-open/nvidia-drm.ko
)

sha256sum "${experimental_modules[@]}" > experimental-modules.sha256
for module in "${experimental_modules[@]}"; do
  modinfo -F filename "$module"
  modinfo -F version "$module"
  modinfo -F vermagic "$module"
done

uname -r
modinfo -n nvidia || true
modinfo -n nvidia_modeset || true
modinfo -n nvidia_drm || true
```

Do not continue unless all experimental files exist, their `vermagic` matches the target kernel, and the installed userspace/GSP stack is the matching NVIDIA release.

## Approved runtime sequence

Execute from SSH after the checkpoint. Save all output in a new artifact directory. These commands deliberately use exact local paths rather than `modprobe`, which could silently select the installed known-good modules.

```bash
artifact_dir="artifacts/EXP-0006-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$artifact_dir"
scripts/collect-native-baseline.sh "$artifact_dir/preload-baseline"
cp experimental-modules.sha256 "$artifact_dir/"

# Stop users of the active display stack before replacement.
sudo systemctl isolate multi-user.target

# Remove the known-good display modules in dependency order. Stop on failure.
sudo modprobe -r nvidia_drm nvidia_modeset nvidia_uvm nvidia_peermem nvidia

# Load the exact locally built experimental files in dependency order.
sudo insmod "$(realpath kernel-open/nvidia.ko)"
sudo insmod "$(realpath kernel-open/nvidia-modeset.ko)"
sudo insmod "$(realpath kernel-open/nvidia-drm.ko)" modeset=1 hdcp_probe=1

# Verify that the opt-in diagnostic is active before accepting any log as evidence.
test "$(cat /sys/module/nvidia_drm/parameters/hdcp_probe)" = "Y"
cat /sys/module/nvidia/version | tee "$artifact_dir/loaded-nvidia-version.txt"
cat /sys/module/nvidia_drm/parameters/hdcp_probe \
  | tee "$artifact_dir/loaded-hdcp-probe-parameter.txt"

sudo journalctl -k -b --no-pager | grep 'HDCP_PROBE' \
  | tee "$artifact_dir/hdcp-probe.log"
python3 scripts/decode-hdcp-probe.py "$artifact_dir/hdcp-probe.log" \
  | tee "$artifact_dir/hdcp-probe.json"
find "$artifact_dir" -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$artifact_dir/artifacts.sha256"
```

If any unload, insertion, version, parameter, or connector-identity check fails, classify the run `INCONCLUSIVE` and restore the known-good stack. Do not improvise around a failure.

## Required controls

- **Default-off control:** repeat with the same exact experimental files but omit `hdcp_probe=1`; there must be no `HDCP_PROBE` line.
- **Repeatability:** reproduce after a clean boot at least twice.
- **Topology:** confirm `/sys/class/drm` identifies the active physical connector as `nvidia-drm` DisplayPort SST.
- **Module identity:** preserve local module hashes, target-kernel `vermagic`, loaded NVIDIA version, and parameter state.
- **Error preservation:** retain raw transport, query result, RM status, flags, and validity.
- **No protection claim:** an unauthenticated/unencrypted result is expected when no client requested protection.

## Gate 1 verdicts

- `COMMUNITY_PATH_CONFIRMED`: transport succeeds, detailed query succeeds, `valid=1`, and capability/state observations are plausible under controls.
- `NARROW_NVIDIA_HOOK_REQUIRED`: the public route reaches the expected owner but a specific missing authorization or context is demonstrated.
- `VENDOR_BACKEND_BLOCKED`: a supported direct-DP route reproducibly fails at RM/GSP with preserved status.
- `INCONCLUSIVE`: topology, module identity, or observations are ambiguous.

## Rollback

The recovery checklist must contain machine-specific rollback commands. The intended normal path is:

```bash
sudo modprobe -r nvidia_drm nvidia_modeset nvidia
sudo modprobe nvidia_drm modeset=1
sudo systemctl isolate graphical.target
```

Confirm the reloaded module paths are the recorded known-good installed paths. If the graphical stack does not recover, remain on SSH/TTY and use the tested known-good boot entry. Do not begin authentication control or KMS property work until the Gate 1 evidence is reviewed.
