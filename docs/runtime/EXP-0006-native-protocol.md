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

Run from a clean checkout of the merged repository on the native test machine. This phase writes evidence files but never changes the driver or boot state.

```bash
set -u
preflight_dir="artifacts/EXP-0006-preflight-$(date -u +%Y%m%dT%H%M%SZ)"
preflight_status=0
python3 scripts/exp0006-preflight.py --output-dir "$preflight_dir" \
  || preflight_status=$?

if [[ "$preflight_status" -eq 0 ]]; then
  python3 scripts/render-exp0006-rollback.py \
    "$preflight_dir/known-good-modules.json" \
    --output "$preflight_dir/rollback-plan.md"
  (
    cd "$preflight_dir"
    find . -type f ! -name artifacts.sha256 -print0 \
      | sort -z \
      | xargs -0 sha256sum > artifacts.sha256
    sha256sum -c artifacts.sha256
  )
else
  printf 'EXP-0006 preflight blocked with status %s; inspect %s and rerun in a new directory after fixing every blocker.\n' \
    "$preflight_status" "$preflight_dir" >&2
  exit "$preflight_status"
fi
```

Exit status `2` means at least one automatic blocker exists. A status-0 report will still contain `WARN` items for human recovery facts or unavailable identity comparisons. Resolve and record every warning before approval.

Store `rollback-plan.md`, `known-good-modules.json`, and `artifacts.sha256` on a second device before any module action.

## Phase B: human recovery checkpoint

Complete every item in `docs/recovery/native-test-recovery-checklist.md` and fill in `docs/runtime/EXP-0006-approval-template.md`.

The approval must bind:

- repository commit;
- exact target kernel;
- preflight and known-good snapshot hashes;
- an absolute local path to the approved exact-kernel build;
- exact build-manifest and build-package hashes;
- module signer/Secure Boot state;
- each stop, unload, load, control, restore, and reboot operation separately.

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
  python3 - <<'PY'
import json
from pathlib import Path
m = json.loads(Path('manifest.json').read_text())
c = m['cleanup']
assert c['preclean_returncode'] == 0
assert c['build_returncode'] == 0
assert c['postclean_returncode'] == 0
assert c['clean_tree_verified'] is True
assert m['source']['dirty'] is False
PY
)
```

The build tool:

- requires the merged symbols in a clean Git checkout;
- runs `make clean` before and after the exact-kernel build;
- verifies the repository is clean again and expected `.ko` outputs are gone;
- uses fixed build user/host strings instead of embedding the account or hostname;
- fails unless all five expected modules report NVIDIA version `610.57.04` and target-kernel `vermagic`;
- copies validated modules into a new evidence directory and never installs or loads them.

When Secure Boot enforcement is active, do not attempt an unsigned module. The build tool accepts `--sign-key` and `--sign-cert`, but key enrollment and a tested recovery path remain separate manual prerequisites. Private key material is never copied into the artifact directory.

## Phase D: bind the approved build

Variables do not survive a clean boot. At the start of **every** runtime session, set the absolute build path and manifest hash copied from the completed approval record. Placeholder values below are deliberately invalid and must be replaced.

```bash
approved_build_dir='/REPLACE/WITH/ABSOLUTE/APPROVED/BUILD/DIRECTORY'
approved_manifest_sha256='REPLACE_WITH_64_LOWERCASE_HEX_CHARACTERS'

[[ "$approved_build_dir" = /* ]]
[[ "$approved_manifest_sha256" =~ ^[0-9a-f]{64}$ ]]
build_dir="$(realpath -- "$approved_build_dir")"
test -d "$build_dir/modules"
test "$(sha256sum "$build_dir/manifest.json" | awk '{print $1}')" \
  = "$approved_manifest_sha256"
(
  cd "$build_dir"
  sha256sum -c artifacts.sha256
)
```

Do not continue if the path, source commit, target kernel, signature state, manifest hash, package hashes, or module metadata differ from the approval record.

## Phase E: common approved-session helpers

Use one default-off session and two enabled sessions, each beginning from a clean boot into the independently verified known-good stack. Execute from working SSH, with local TTY recovery also proven. Never use force-removal.

Run these definitions at the beginning of each approved session after binding `build_dir` and `approved_manifest_sha256`:

```bash
set -euo pipefail
trap 'printf "EXP-0006 session interrupted; remain in text mode and execute the offline approved rollback plan.\n" >&2' ERR INT TERM

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

verify_direct_dp_topology() {
  local status connector driver
  local -a connected=()
  while IFS= read -r -d '' status; do
    if [[ "$(cat "$status")" = connected ]]; then
      connected+=("$(basename "$(dirname "$status")")")
    fi
  done < <(
    find /sys/class/drm -maxdepth 2 -path '/sys/class/drm/card*-*/status' -print0 \
      | sort -z
  )
  [[ "${#connected[@]}" -eq 1 ]]
  connector="${connected[0]}"
  [[ "$connector" =~ ^card[0-9]+-DP-[0-9]+$ ]]
  driver="$(basename "$(readlink -f "/sys/class/drm/$connector/device/driver")")"
  [[ "$driver" = nvidia ]]
  printf '%s\n' "$connector"
}

verify_loaded_build() {
  local expected_probe="$1"
  local output="$2"
  python3 scripts/verify-exp0006-loaded.py \
    --manifest "$build_dir/manifest.json" \
    --expected-manifest-sha256 "$approved_manifest_sha256" \
    --expect-probe "$expected_probe" \
    --output "$output"
}
```

The loaded-build verifier checks the approved manifest hash, staged module hashes, clean source/build record, target kernel, loaded module versions and `srcversion`, and `nvidia_drm` parameters. It does not infer HDCP capability from those checks.

## Session 1: default-off negative control

Rebind the approved build as described in Phase D, define the Phase E helpers, and then run:

```bash
artifact_dir="artifacts/EXP-0006-negative-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$artifact_dir"
scripts/collect-native-baseline.sh "$artifact_dir/preload-baseline"
cp "$build_dir/manifest.json" "$artifact_dir/approved-build-manifest.json"
printf '%s  approved-build-manifest.json\n' "$approved_manifest_sha256" \
  > "$artifact_dir/approved-build-manifest.sha256"
start_time="$(date --iso-8601=seconds)"

sudo systemctl isolate multi-user.target
unload_nvidia_stack

sudo insmod "$(realpath "$build_dir/modules/nvidia.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-modeset.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-drm.ko")" modeset=1

verify_loaded_build N "$artifact_dir/loaded-build.json"
modetest -M nvidia-drm -c \
  >"$artifact_dir/modetest.stdout.txt" \
  2>"$artifact_dir/modetest.stderr.txt"
verify_direct_dp_topology \
  | tee "$artifact_dir/connected-connector.txt"
sudo journalctl -k -b --since "$start_time" --no-pager \
  >"$artifact_dir/kernel.log"
if grep -q 'HDCP_PROBE' "$artifact_dir/kernel.log"; then
  echo 'FAIL: default-off control emitted HDCP_PROBE' >&2
  exit 1
fi
find "$artifact_dir" -type f ! -name artifacts.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum >"$artifact_dir/artifacts.sha256"
```

Immediately execute the reviewed offline rollback plan, verify the restored module paths/hashes/version/`vermagic`/`srcversion` and graphical target, record the result, and reboot to the known-good entry before Session 2.

## Session 2: first enabled read-only run

Start from a clean known-good boot. Rebind the approved build and redefine the common helpers, then run:

```bash
artifact_dir="artifacts/EXP-0006-enabled-1-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$artifact_dir"
scripts/collect-native-baseline.sh "$artifact_dir/preload-baseline"
cp "$build_dir/manifest.json" "$artifact_dir/approved-build-manifest.json"
printf '%s  approved-build-manifest.json\n' "$approved_manifest_sha256" \
  > "$artifact_dir/approved-build-manifest.sha256"
start_time="$(date --iso-8601=seconds)"

sudo systemctl isolate multi-user.target
unload_nvidia_stack

sudo insmod "$(realpath "$build_dir/modules/nvidia.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-modeset.ko")"
sudo insmod "$(realpath "$build_dir/modules/nvidia-drm.ko")" \
  modeset=1 hdcp_probe=1

verify_loaded_build Y "$artifact_dir/loaded-build.json"
modetest -M nvidia-drm -c \
  >"$artifact_dir/modetest.stdout.txt" \
  2>"$artifact_dir/modetest.stderr.txt"
verify_direct_dp_topology \
  | tee "$artifact_dir/connected-connector.txt"
sudo journalctl -k -b --since "$start_time" --no-pager \
  >"$artifact_dir/kernel.log"
grep 'HDCP_PROBE' "$artifact_dir/kernel.log" \
  | tee "$artifact_dir/hdcp-probe.log"
python3 scripts/decode-hdcp-probe.py "$artifact_dir/hdcp-probe.log" \
  | tee "$artifact_dir/hdcp-probe.json"
find "$artifact_dir" -type f ! -name artifacts.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum >"$artifact_dir/artifacts.sha256"
```

Immediately restore and verify the known-good stack, record the result, and reboot to the known-good entry before Session 3.

## Session 3: enabled clean-boot replication

Repeat the complete Session 2 sequence without changing the source commit, build directory, manifest hash, cable, display, mode, or topology. Use a fresh directory named:

```text
artifacts/EXP-0006-enabled-2-<UTC_TIMESTAMP>
```

Rebind and reverify the approved build after the clean boot. Any difference in module identity, topology, procedure, or restoration makes the comparison `INCONCLUSIVE`. Restore and verify the known-good stack again after collection.

## Required controls

- **Default-off:** the same exact experimental build without `hdcp_probe=1` emits no `HDCP_PROBE` record after a successful connector query.
- **Enabled repeatability:** the enabled observation is reproduced in two separately booted sessions using the identical approved build and direct-DP topology.
- **Topology:** sysfs and successful `modetest` output show one physical NVIDIA DisplayPort SST connector in every session.
- **Module identity:** preserve and reverify source commit, manifest hash, local module hashes, target-kernel identity, signatures, loaded version/`srcversion`, and parameter state.
- **Recovery:** verify the known-good stack after each session; a failed or ambiguous restoration invalidates that session.
- **Error preservation:** retain raw transport result, detailed query result, RM status, flags, validity, complete kernel log, stdout, stderr, and hashes.
- **No protection claim:** unauthenticated and unencrypted state is expected because no client requested protection.

## Gate 1 verdicts

- `COMMUNITY_PATH_CONFIRMED`: transport succeeds, the detailed query succeeds, `valid=1`, and capability/state observations are plausible and repeatable under all controls.
- `NARROW_NVIDIA_HOOK_REQUIRED`: the public route reaches the expected owner but a specific missing authorization or context is demonstrated.
- `VENDOR_BACKEND_BLOCKED`: a supported direct-DP route reproducibly fails at RM/GSP with preserved status.
- `INCONCLUSIVE`: topology, module identity, recovery, negative control, repeatability, or observations are ambiguous.

Do not begin authentication control, Type 1 selection, KMS property work, protected decode, or service testing until all three sessions have been reviewed and one Gate 1 verdict has been assigned.
