#!/usr/bin/env bash
set -u

OUT_DIR="${1:-artifacts/native-baseline-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT_DIR/raw"

run() {
    local name="$1"; shift
    {
        printf '$'
        printf ' %q' "$@"
        printf '\n'
        "$@"
    } >"$OUT_DIR/raw/${name}.stdout.txt" 2>"$OUT_DIR/raw/${name}.stderr.txt"
    printf '%s\t%s\n' "$name" "$?" >> "$OUT_DIR/exit-codes.tsv"
}

printf 'name\texit_code\n' > "$OUT_DIR/exit-codes.tsv"
run date date --iso-8601=seconds
run uname uname -a
run os-release sh -c 'cat /etc/os-release'
run lspci-nvidia sh -c "lspci -Dnnk | sed -n '/VGA compatible controller.*NVIDIA/,+4p;/3D controller.*NVIDIA/,+4p'"
run kernel-cmdline sh -c "cat /proc/cmdline | sed -E 's/(BOOT_IMAGE|root|resume)=[^ ]+/\\1=<redacted>/g'"
run loaded-modules sh -c "lsmod | grep -E '^(nvidia|nouveau)' || true"
run nvidia-module-version modinfo -F version nvidia
run nvidia-drm-module-version modinfo -F version nvidia_drm
run nvidia-smi-safe sh -c "nvidia-smi --query-gpu=name,pci.bus_id,driver_version,vbios_version,display_active,display_mode --format=csv,noheader 2>/dev/null || true"
run drm-links sh -c 'for p in /sys/class/drm/card*-*; do [ -e "$p" ] || continue; printf "%s\t" "$p"; readlink -f "$p/device/driver"; done'
run drm-info sh -c 'command -v drm_info >/dev/null && drm_info || true'
run modetest-nvidia sh -c 'command -v modetest >/dev/null && modetest -M nvidia-drm -c || true'
run vulkan-summary sh -c 'command -v vulkaninfo >/dev/null && vulkaninfo --summary || true'
run display-properties sh -c 'for p in /sys/class/drm/card*-*/status; do printf "%s: " "$p"; cat "$p"; done'
run edid-hashes sh -c 'for p in /sys/class/drm/card*-*/edid; do [ -s "$p" ] || continue; printf "%s  " "$p"; sha256sum "$p" | cut -d" " -f1; done'
run recent-nvidia-kernel-log sh -c "dmesg 2>/dev/null | grep -Ei 'nvidia|nvrm|hdcp|drm' | tail -n 1000 | sed -E 's/([[:alnum:]_.-]+) kernel:/<host> kernel:/' || true"

cat > "$OUT_DIR/README.txt" <<'EOF'
Native Linux baseline collector.

Review every file before publishing. The collector stores EDID hashes, not EDID bytes, and limits nvidia-smi fields to non-unique diagnostics. It does not require sudo and records unavailable tools as failed or empty commands.
EOF

(
    cd "$OUT_DIR"
    find . -type f ! -name artifacts.sha256 -print0 | sort -z | xargs -0 sha256sum > artifacts.sha256
)
printf 'Baseline written to %s\n' "$OUT_DIR"
