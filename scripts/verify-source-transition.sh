#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-artifacts/source-transition}"
mkdir -p "$OUT_DIR"

PRE="2ccbad25e1af6a6ee6f38cf569f89f8b65d658ab"
FIRST="2c7bfb47060233bda7c37c8065c0ddcac0d3da05"
CURRENT="e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb"
DP_PATH="src/common/displayport/src/dp_evoadapter.cpp"
GROUP_PATH="src/common/displayport/src/dp_groupimpl.cpp"
KAPI_PATH="kernel-open/common/inc/nvkms-kapi.h"
DRM_PATH="kernel-open/nvidia-drm/nvidia-drm-connector.c"

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

for rev in "$PRE" "$FIRST" "$CURRENT"; do
    git cat-file -e "${rev}^{commit}" 2>/dev/null || fail "missing commit $rev; use a checkout with full history"
done

pre_text="$(git show "$PRE:$DP_PATH")"
first_text="$(git show "$FIRST:$DP_PATH")"
current_text="$(git show "$CURRENT:$DP_PATH")"
current_group="$(git show "$CURRENT:$GROUP_PATH")"
current_kapi="$(git show "$CURRENT:$KAPI_PATH")"
current_drm="$(git show "$CURRENT:$DRM_PATH")"

grep -Fq 'HDCP Not Supported' <<<"$pre_text" || fail '590.48.01 no longer matches the expected unsupported control'
grep -Fq 'NV0073_CTRL_CMD_SPECIFIC_GET_HDCP_STATE' <<<"$first_text" || fail '595.44.02 lacks the expected RM-backed HDCP state query'
grep -Fq 'NV0073_CTRL_CMD_SPECIFIC_HDCP_CTRL' <<<"$first_text" || fail '595.44.02 lacks the expected HDCP control path'
grep -Fq 'NV0073_CTRL_CMD_SPECIFIC_GET_HDCP_STATE' <<<"$current_text" || fail '610.57.04 lacks the expected HDCP state query'
grep -Fq 'hdcpSetEncrypted' <<<"$current_group" || fail '610.57.04 lacks expected DP group encryption management'

if grep -Fq 'drm_connector_attach_content_protection_property' <<<"$current_drm"; then
    fail 'baseline unexpectedly attaches the standard KMS content-protection property'
fi
if grep -Eq 'queryHdcpState|NvKmsKapiHdcpState' <<<"$current_kapi"; then
    fail 'baseline unexpectedly exposes the proposed HDCP KAPI surface'
fi

extract() {
    local rev="$1" pattern="$2" output="$3"
    git show "$rev:$DP_PATH" | nl -ba | grep -E -C 8 "$pattern" > "$output"
}

extract "$PRE" 'configureHDCP(GetHDCPState|Renegotiate)' "$OUT_DIR/590.48.01.txt"
extract "$FIRST" 'configureHDCP(GetHDCPState|Renegotiate)|GET_HDCP_STATE' "$OUT_DIR/595.44.02.txt"
extract "$CURRENT" 'configureHDCP(GetHDCPState|Renegotiate)|GET_HDCP_STATE' "$OUT_DIR/610.57.04.txt"
git show "$CURRENT:$GROUP_PATH" | nl -ba | grep -E -C 8 'hdcpSetEncrypted|setStreamType' > "$OUT_DIR/610.57.04-group.txt"
git show "$CURRENT:$KAPI_PATH" | sha256sum > "$OUT_DIR/current-kapi.sha256"
git show "$CURRENT:$DRM_PATH" | sha256sum > "$OUT_DIR/current-nvidia-drm-connector.sha256"

(
    cd "$OUT_DIR"
    find . -maxdepth 1 -type f ! -name artifacts.sha256 -print0 | sort -z | xargs -0 sha256sum > artifacts.sha256
)

cat > "$OUT_DIR/verdict.txt" <<EOF
EXP-0001: PASS
Highest state proven: SOURCE_PRESENT
590.48.01: hard-coded unsupported DP HDCP state
595.44.02: RM-backed state/control symbols present
610.57.04: RM-backed state/control and DP group logic present
Standard KMS content-protection attachment: absent in pinned baseline
Dedicated proposed HDCP KAPI: absent in pinned baseline
EOF

cat "$OUT_DIR/verdict.txt"
