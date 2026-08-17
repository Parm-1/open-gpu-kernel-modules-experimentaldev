#!/usr/bin/env bash
set -uo pipefail

OUT_DIR="${1:-artifacts/native-baseline-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_PARENT="$(dirname "$OUT_DIR")"
mkdir -p "$OUT_PARENT"
if ! mkdir "$OUT_DIR"; then
    printf 'Refusing to overwrite baseline directory: %s\n' "$OUT_DIR" >&2
    exit 1
fi
mkdir "$OUT_DIR/raw"

run() {
    local name="$1"; shift
    local status
    {
        printf '$'
        printf ' %q' "$@"
        printf '\n'
        "$@"
    } >"$OUT_DIR/raw/${name}.stdout.txt" 2>"$OUT_DIR/raw/${name}.stderr.txt"
    status=$?
    printf '%s\t%s\n' "$name" "$status" >> "$OUT_DIR/exit-codes.tsv"
}

printf 'name\texit_code\n' > "$OUT_DIR/exit-codes.tsv"
run date date --iso-8601=seconds
# Exclude the nodename/hostname while retaining kernel and architecture identity.
run uname uname -srvmo
run os-release cat /etc/os-release
run lspci-nvidia sh -c "lspci -Dnnk | sed -n '/VGA compatible controller.*NVIDIA/,+4p;/3D controller.*NVIDIA/,+4p'"
# Record only display/driver-relevant kernel parameters; avoid root, resume,
# encrypted-volume, and boot-image identifiers.
run relevant-kernel-parameters sh -c "tr ' ' '\\n' </proc/cmdline | grep -E '^(nvidia|nvidia_drm|nouveau|module_blacklist|modprobe.blacklist|rd.driver.blacklist|ibt|iommu|intel_iommu|amd_iommu|video)=' | sort || true"
run loaded-modules sh -c "lsmod | grep -E '^(nvidia|nouveau)' || true"
run nvidia-module-path modinfo -n nvidia
run nvidia-module-version modinfo -F version nvidia
run nvidia-module-vermagic modinfo -F vermagic nvidia
run nvidia-drm-module-path modinfo -n nvidia_drm
run nvidia-drm-module-version modinfo -F version nvidia_drm
run nvidia-drm-module-vermagic modinfo -F vermagic nvidia_drm
run nvidia-smi-minimal sh -c "nvidia-smi --query-gpu=name,driver_version,display_active,display_mode --format=csv,noheader 2>/dev/null"
run drm-links sh -c 'for p in /sys/class/drm/card*-*; do [ -e "$p" ] || continue; printf "%s\t" "$p"; readlink -f "$p/device/driver"; done'
run modetest-nvidia modetest -M nvidia-drm -c
run vulkan-summary vulkaninfo --summary
run display-properties sh -c 'for p in /sys/class/drm/card*-*/status; do [ -e "$p" ] || continue; printf "%s: " "$p"; cat "$p"; done'
# Record only EDID presence and byte count, never EDID bytes or a persistent hash.
run edid-presence sh -c 'for p in /sys/class/drm/card*-*/edid; do [ -s "$p" ] || continue; printf "%s\t%s bytes\n" "$p" "$(wc -c <"$p")"; done'
run recent-nvidia-kernel-log sh -c "dmesg 2>/dev/null | grep -Ei 'nvidia|nvrm|hdcp|drm' | tail -n 1000 | sed -E 's/GPU-[0-9A-Fa-f-]+/GPU-<redacted>/g; s/([[:alnum:]_.-]+) kernel:/<host> kernel:/' || true"

cat > "$OUT_DIR/README.txt" <<'EOF'
Native Linux baseline collector.

Review every file before sharing. The collector excludes the hostname from its
uname query and stores only EDID presence/size, not EDID bytes or hashes. It
limits nvidia-smi to non-unique operational fields. Local filesystem paths,
PCI topology, kernel parameters, and diagnostic text can still contain
identifying context. The collector does not require sudo and records failed or
unavailable commands rather than fabricating success.
EOF

(
    cd "$OUT_DIR"
    find . -type f ! -name artifacts.sha256 -print0 | sort -z | xargs -0 sha256sum > artifacts.sha256
)
printf 'Baseline written to %s\n' "$OUT_DIR"
