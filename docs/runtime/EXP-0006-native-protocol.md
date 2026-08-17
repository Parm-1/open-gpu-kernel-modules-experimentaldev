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
3. Match kernel modules, NVIDIA userspace, and GSP firmware to 610.57.04.
4. Archive the unmodified baseline from `scripts/collect-native-baseline.sh`.
5. Record explicit approval for the module-load/reboot operation.

## Build-only validation already completed

The branch has repeatedly completed:

```bash
make modules -j2 SYSSRC=<generic-kernel-headers> SYSOUT=<same-headers>
```

That is source/build evidence only, not target-kernel or runtime evidence.

## Approved runtime sequence

Execute from SSH after the checkpoint. Adapt paths to the pinned target kernel and save every command/output in a new artifact directory.

```bash
artifact_dir="artifacts/EXP-0006-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$artifact_dir"
scripts/collect-native-baseline.sh "$artifact_dir/preload-baseline"

# Stop the graphical session before replacing the display stack.
sudo systemctl isolate multi-user.target

# Load the matching experimental stack through the prepared local install.
# Exact install/rollback commands must be written into the recovery checklist.
sudo modprobe nvidia
sudo modprobe nvidia_modeset
sudo modprobe nvidia_drm modeset=1 hdcp_probe=1

sudo journalctl -k -b --no-pager | grep 'HDCP_PROBE' \
  | tee "$artifact_dir/hdcp-probe.log"
python3 scripts/decode-hdcp-probe.py "$artifact_dir/hdcp-probe.log" \
  | tee "$artifact_dir/hdcp-probe.json"
sha256sum "$artifact_dir"/* > "$artifact_dir/artifacts.sha256"
```

Do not proceed if the experimental modules cannot be unambiguously distinguished from the installed known-good modules.

## Required controls

- **Default-off control:** load the same build without `hdcp_probe=1`; there must be no `HDCP_PROBE` line.
- **Repeatability:** reproduce after a clean boot at least twice.
- **Topology:** confirm `/sys/class/drm` identifies the active physical connector as `nvidia-drm` DisplayPort SST.
- **Error preservation:** retain raw transport, query result, RM status, flags, and validity.
- **No protection claim:** an unauthenticated/unencrypted result is expected when no client requested protection.

## Gate 1 verdicts

- `COMMUNITY_PATH_CONFIRMED`: transport succeeds, detailed query succeeds, `valid=1`, and capability/state changes are plausible under controls.
- `NARROW_NVIDIA_HOOK_REQUIRED`: public route reaches the expected owner but a specific missing authorization/context is demonstrated.
- `VENDOR_BACKEND_BLOCKED`: a supported direct-DP route reproducibly fails at RM/GSP with preserved status.
- `INCONCLUSIVE`: topology, module identity, or observations are ambiguous.

After collection, restore the known-good stack before returning to graphical mode. Do not begin authentication control or KMS property work until the Gate 1 evidence is reviewed.
