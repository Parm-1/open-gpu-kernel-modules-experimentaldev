# EXP-0006 native runtime protocol

Status: `BLOCKED_PENDING_PREFLIGHT_RECOVERY_REVIEW_AND_EXPLICIT_LOAD_APPROVAL`

## Objective

Classify whether the RTX 2060's native Linux RM/GSP path permits the compiled read-only HDCP state query. This protocol performs no authentication request, stream-type selection, KMS content-protection property change, protected playback, or service test.

## Required topology

```text
RTX 2060 → direct DisplayPort cable → one HDCP 2.2/2.3-capable display
```

Use native x86-64 Linux, SDR 1920×1080 60 Hz, no secondary output, MST, adapter, dock, KVM, receiver, capture device, HDR, or VRR.

## Phase A: read-only host preflight

Run from the merged repository on the native test machine. This phase never changes the driver or boot state.

```bash
preflight_dir="artifacts/EXP-0006-preflight-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/exp0006-preflight.py --output-dir "$preflight_dir"
python3 scripts/render-exp0006-rollback.py \
  "$preflight_dir/known-good-modules.json" \
  --output "$preflight_dir/rollback-plan.md"
(
  cd "$preflight_dir"
  sha256sum -c artifacts.sha256
)
```

Exit status `2` means at least one blocker exists. Do not build or request runtime approval until every `BLOCK` result is resolved. `WARN` results include manual recovery and display-mode checks that cannot be proven by a script.

Store `rollback-plan.md`, `known-good-modules.json`, and `artifacts.sha256` on a second device before any module action.

## Phase B: human recovery checkpoint

Complete every item in `docs/recovery/native-test-recovery-checklist.md` and fill in `docs/runtime/EXP-0006-approval-template.md`.

The approval must identify:

- repository commit;
- exact target kernel;
- preflight artifact hash;
- exact-kernel build manifest hash;
- known-good module snapshot hash;
- whether stopping the graphical target and unloading/loading modules is approved;
- whether a reboot is separately approved.

Approval for source work or building is not approval to load modules. A reboot is not implied by module-load approval.

## Phase C: exact-target-kernel build

Build on the native test machine against the running kernel. GitHub's generic-header build is useful CI evidence but is not a runtime artifact.

```bash
build_dir="artifacts/EXP-0006-build-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/build-exp0006.py --output-dir "$build_dir"
(
  cd "$build_dir"
  sha256sum -c artifacts.sha256
  python3 -m json.tool manifest.json >/dev/null
)
```

The build tool fails closed unless all five expected NVIDIA modules report version `610.57.04` and a `vermagic` matching the target kernel. It copies modules into a new evidence directory and does not install or load them.

When Secure Boot enforcement is active, do not attempt an unsigned module. The build tool accepts `--sign-key` and `--sign-cert`, but key enrollment and a tested recovery path remain separate manual prerequisites. Private key material is never copied into the artifact directory.

## Phase D: prove module identity

Before approval is exercised, preserve these outputs with the build artifacts:

```bash
uname -r
cat "$build_dir/manifest.json"
sha256sum "$build_dir"/modules/*.ko
for module in "$build_dir"/modules/*.ko; do
  printf '\n== %s ==\n' "$module"
  modinfo -F filename "$module"
  modinfo -F version "$module"
  modinfo -F vermagic "$module"
  modinfo -F signer "$module"
done
```

Do not continue if the source commit, module version, target-kernel `vermagic`, signature state, or hashes are ambiguous.

## Phase E: approved runtime sessions

Use two clean-boot sessions. Execute from working SSH, with local TTY recovery also proven. The commands intentionally use exact local paths rather than `modprobe` for the experimental files.

For both sessions, use this fail-closed helper after stopping the graphical target. It removes only NVIDIA modules that are actually present and verifies that none remain. Never use force-removal.

```bash
unload_nvidia_stack() {
  local module
  for module in nvidia_drm nvidia_modeset nvidia_uvm nvidia_peermem nvidia; do
    if [[ -d "/sys/module/$module" ]]; then
      sudo modprobe -r "$module"
    fi
  done
  for module in nvidia_drm nvidia_modeset nvidia_uvm nvidia_peermem nvidia; do
    if [[ -d "/sys/module/$module" ]]; then
      echo "FAIL: $module is still loaded" >&2
      return 1
    fi
  done
}
```

### Session 1: default-off negative control

```bash
artifact_dir="artifacts/EXP-0006-negative-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$artifact_dir"
scripts/collect-native-baseline.sh "$artifact_dir/preload-baseline"
start_time="$(date --iso-8601=seconds)"

sudo systemctl isolate multi-user.target
unload_nvidia_stack

sudo insmod "$(realpath "$build_dir/modules/nvidia.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-modeset.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-drm.ko")" modeset=1

test "$(cat /sys/module/nvidia_drm/parameters/hdcp_probe)" = "N"
modetest -M nvidia-drm -c \
  >"$artifact_dir/modetest.stdout.txt" \
  2>"$artifact_dir/modetest.stderr.txt" || true
sudo journalctl -k -b --since "$start_time" --no-pager \
  >"$artifact_dir/kernel.log"
if grep -q 'HDCP_PROBE' "$artifact_dir/kernel.log"; then
  echo 'FAIL: default-off control emitted HDCP_PROBE' >&2
  exit 1
fi
```

Restore the known-good stack using the reviewed machine-specific rollback plan, verify its paths and version, and reboot to the known-good entry before Session 2.

### Session 2: read-only probe enabled

```bash
artifact_dir="artifacts/EXP-0006-probe-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$artifact_dir"
scripts/collect-native-baseline.sh "$artifact_dir/preload-baseline"
start_time="$(date --iso-8601=seconds)"

sudo systemctl isolate multi-user.target
unload_nvidia_stack

sudo insmod "$(realpath "$build_dir/modules/nvidia.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-modeset.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-drm.ko")" \
  modeset=1 hdcp_probe=1

test "$(cat /sys/module/nvidia_drm/parameters/hdcp_probe)" = "Y"
cat /sys/module/nvidia/version \
  | tee "$artifact_dir/loaded-nvidia-version.txt"
cat /sys/module/nvidia_drm/parameters/hdcp_probe \
  | tee "$artifact_dir/loaded-hdcp-probe-parameter.txt"

modetest -M nvidia-drm -c \
  >"$artifact_dir/modetest.stdout.txt" \
  2>"$artifact_dir/modetest.stderr.txt" || true
sudo journalctl -k -b --since "$start_time" --no-pager \
  | tee "$artifact_dir/kernel.log"
grep 'HDCP_PROBE' "$artifact_dir/kernel.log" \
  | tee "$artifact_dir/hdcp-probe.log"
python3 scripts/decode-hdcp-probe.py "$artifact_dir/hdcp-probe.log" \
  | tee "$artifact_dir/hdcp-probe.json"
find "$artifact_dir" -type f -print0 | sort -z | xargs -0 sha256sum \
  >"$artifact_dir/artifacts.sha256"
```

Restore and verify the known-good stack before returning to graphical mode. If any unload, insertion, version, parameter, connector-identity, decode, or restoration check fails, stop and classify the session `INCONCLUSIVE`. Never use force-removal or improvise around a failed recovery check.

## Required controls

- **Default-off:** the same exact experimental build without `hdcp_probe=1` emits no `HDCP_PROBE` record.
- **Repeatability:** reproduce the enabled result after at least two clean boots.
- **Topology:** `/sys/class/drm` and `modetest` show one physical NVIDIA DisplayPort SST connector.
- **Module identity:** preserve source commit, local module hashes, target-kernel `vermagic`, signatures, loaded NVIDIA version, and parameter state.
- **Error preservation:** retain raw transport result, detailed query result, RM status, flags, validity, complete kernel log, stdout, and stderr.
- **No protection claim:** unauthenticated and unencrypted state is expected because no client requested protection.

## Gate 1 verdicts

- `COMMUNITY_PATH_CONFIRMED`: transport succeeds, the detailed query succeeds, `valid=1`, and capability/state observations are plausible and repeatable under all controls.
- `NARROW_NVIDIA_HOOK_REQUIRED`: the public route reaches the expected owner but a specific missing authorization or context is demonstrated.
- `VENDOR_BACKEND_BLOCKED`: a supported direct-DP route reproducibly fails at RM/GSP with preserved status.
- `INCONCLUSIVE`: topology, module identity, recovery, or observations are ambiguous.

Do not begin authentication control, Type 1 selection, KMS property work, protected decode, or service testing until the Gate 1 evidence has been reviewed and one verdict has been assigned.
